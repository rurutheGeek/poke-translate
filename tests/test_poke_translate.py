"""Dictionary, core and build checks for poke-translate."""

import importlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STACK = ROOT
sys.path.insert(0, str(STACK))
dictionary = importlib.import_module('dictionary')

TABLES = {
    'pokemon_species_names': 'pokemon_species_id,local_language_id,name,genus\n'
                             '445,11,ガブリアス,\n445,1,ガブリアス,マッハポケモン\n445,9,Garchomp,Mach Pokémon\n'
                             '6,1,リザードン,\n6,9,Charizard,\n',
    'move_names': 'move_id,local_language_id,name\n89,1,じしん\n89,9,Earthquake\n'
                  '94,1,サイコキネシス\n94,9,Psychic\n',
    'ability_names': 'ability_id,local_language_id,name\n24,1,さめはだ\n24,9,Rough Skin\n',
    'item_names': 'item_id,local_language_id,name\n264,1,こだわりスカーフ\n264,9,Choice Scarf\n',
    'type_names': 'type_id,local_language_id,name\n12,1,くさ\n12,9,Grass\n14,1,エスパー\n14,9,Psychic\n',
    'nature_names': 'nature_id,local_language_id,name\n2,1,ずぶとい\n2,9,Bold\n',
    'location_names': 'location_id,local_language_id,name\n',
    'pokemon_form_names': 'pokemon_form_id,local_language_id,form_name,pokemon_name\n'
                          '10134,1,メガリザードンＸ,\n10134,9,Mega Charizard X,Mega Charizard X\n'
                          '10193,1,アローラのすがた,\n10081,1,れいじゅうフォルム,\n',
    'stat_names': 'stat_id,local_language_id,name\n6,1,すばやさ\n6,9,Speed\n7,1,めいちゅう\n7,9,accuracy\n',
    'pokemon_forms': 'id,identifier,form_identifier,pokemon_id\n'
                     '10134,charizard-mega-x,mega-x,10034\n10081,landorus-therian,therian,10021\n'
                     '6,charizard,,6\n',
    'pokemon': 'id,identifier,species_id\n6,charizard,6\n10034,charizard-mega-x,6\n'
               '10021,landorus-therian,645\n',
}
TABLES['pokemon_species_names'] += '645,1,ランドロス,\n645,9,Landorus,\n'


class DictionaryTests(unittest.TestCase):
    def test_kana_names_are_canonical_and_kanji_names_are_aliases(self):
        entries = dictionary.parse_csvs(TABLES)
        self.assertEqual(entries['species:445']['ja'][0], 'ガブリアス')
        self.assertEqual(entries['move:89']['en'], ['Earthquake'])

    def test_forms_keep_only_full_names_and_add_halfwidth_variants(self):
        entries = dictionary.parse_csvs(TABLES)
        self.assertEqual(entries['form:10134']['ja'], ['メガリザードンＸ', 'メガリザードンX'])
        self.assertNotIn('form:10193', entries)

    def test_type_words_are_generated_for_explicit_type_mentions(self):
        typed = dictionary.parse_csvs(TABLES)['type:12:typed']
        self.assertEqual(typed['ja'], ['くさタイプ'])
        self.assertEqual(typed['en'], ['Grass-type', 'Grass-types', 'Grass type', 'Grass types'])

    def test_stats_skip_accuracy_and_evasion(self):
        entries = dictionary.parse_csvs(TABLES)
        self.assertEqual(entries['stat:6']['ja'], ['すばやさ'])
        self.assertNotIn('stat:7', entries)

    def test_overseas_form_names_map_to_japanese_names(self):
        entries = dictionary.parse_csvs(TABLES)
        self.assertEqual(entries['form:10081']['ja'][0], 'ランドロス（れいじゅうフォルム）')
        self.assertEqual(entries['form:10081']['en'], ['Landorus-Therian'])
        self.assertIn('Charizard-Mega-X', entries['form:10134']['en'])
        self.assertEqual(entries['form:10134']['ja'][0], 'メガリザードンＸ')

    def test_type_phrases_and_showdown_nature_lines_are_generated(self):
        entries = dictionary.parse_csvs(TABLES)
        self.assertEqual(entries['type:14:無効'], {'ja': ['エスパー無効'],
                                                  'en': ['Psychic immunity', 'Psychic immunities']})
        self.assertEqual(entries['type:12:tera'], {'ja': ['くさテラス'], 'en': ['Tera Grass']})
        self.assertEqual(entries['nature:2:line'], {'ja': ['性格: ずぶとい'], 'en': ['Bold Nature']})

    def test_custom_terms_extend_or_add_and_unknown_refs_fail(self):
        base = {'entries': dictionary.parse_csvs(TABLES)}
        built = dictionary.build(base, {'terms': [{'ref': 'species:445', 'ja': ['ガブ']},
                                                  {'ja': ['S振り'], 'en': 'Speed investment'}],
                                        'ambiguous': {'en': ['Bold']}})
        self.assertIn('ガブ', built['entries']['species:445']['ja'])
        self.assertEqual(built['entries']['custom:1'],
                         {'ja': ['S振り'], 'en': ['Speed investment'], '_custom': True})
        self.assertEqual(built['ambiguous'], {'en': ['Bold']})
        with self.assertRaises(ValueError):
            dictionary.build(base, {'terms': [{'ref': 'species:99999', 'ja': ['x']}]})

    def test_the_committed_custom_terms_are_well_formed(self):
        custom = json.loads((STACK / 'custom-terms.json').read_text(encoding='utf-8'))
        for term in custom['terms']:
            if 'ref' in term:
                self.assertRegex(term['ref'], r'^[a-z]+:\d+$')
            else:
                self.assertIn('ja', term)
                self.assertIn('en', term)
        languages = set(dictionary.LANGUAGES.values())
        self.assertLessEqual(set(custom['exclude']) | set(custom['ambiguous']), languages)

    def test_pokeapi_is_fetched_at_the_requested_ref(self):
        seen = []

        def opener(url, timeout):
            seen.append(url)
            return io.BytesIO(TABLES[url.rsplit('/', 1)[1][:-4]].encode('utf-8'))

        built = dictionary.fetch_pokeapi('abc123', opener)
        self.assertEqual(built['source'], 'PokeAPI/pokeapi@abc123')
        self.assertTrue(all('/abc123/data/v2/csv/' in url for url in seen))


FIXTURE_CUSTOM = {
    'terms': [{'ref': 'species:445', 'ja': ['ガブ']}, {'ja': ['タイプ一致'], 'en': ['STAB']}],
    'ambiguous': {}, 'exclude': {},
}


class CoreTests(unittest.TestCase):
    """core/poketr.js の照合・翻訳を node --test で確かめる。"""

    def test_javascript_core(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node is not installed')
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / 'dictionary.json'
            built = dictionary.build({'entries': dictionary.parse_csvs(TABLES)}, FIXTURE_CUSTOM)
            fixture.write_text(json.dumps(built, ensure_ascii=False), encoding='utf-8')
            result = subprocess.run(
                [node, '--test', str(STACK / 'core/poketr.test.js')],
                env={**os.environ, 'POKETR_FIXTURE': str(fixture)},
                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class ExtensionTests(unittest.TestCase):
    def setUp(self):
        self.extension = STACK / 'extension'
        self.manifest = json.loads((self.extension / 'manifest.json').read_text(encoding='utf-8'))

    def test_manifest_v3_references_existing_files(self):
        self.assertEqual(self.manifest['manifest_version'], 3)
        for name in [self.manifest['background']['service_worker'],
                     self.manifest['options_ui']['page'], 'content.js', 'content.css', 'options.js']:
            self.assertTrue((self.extension / name).is_file(), name)

    def test_translation_runs_in_the_service_worker_without_a_server(self):
        # ページ側から fetch すると閲覧中サイトの CORS・CSP を受ける。
        self.assertNotIn('fetch(', (self.extension / 'content.js').read_text(encoding='utf-8'))
        background = (self.extension / 'background.js').read_text(encoding='utf-8')
        self.assertIn("importScripts('poketr.js')", background)
        self.assertEqual(self.manifest['host_permissions'], ['https://translate.googleapis.com/*'])

    def test_bundled_core_and_dictionary_are_generated_not_committed(self):
        for name in ['poketr.js', 'dictionary.json']:
            ignored = subprocess.run(['git', 'check-ignore', '-q', str(self.extension / name)], cwd=ROOT)
            self.assertEqual(ignored.returncode, 0, name)

    def test_code_blocks_and_inputs_are_not_translated(self):
        content = (self.extension / 'content.js').read_text(encoding='utf-8')
        for tag in ['PRE', 'CODE', 'TEXTAREA', 'INPUT', 'SCRIPT', 'STYLE', 'POKE-TR']:
            self.assertIn(f"'{tag}'", content)


class BuildTests(unittest.TestCase):
    def test_build_writes_the_site_extension_and_reproducible_release_archives(self):
        build = importlib.import_module('build')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(STACK / 'extension', root / 'extension',
                            ignore=shutil.ignore_patterns('poketr.js', 'dictionary.json'))
            (root / 'custom-terms.json').write_text(json.dumps(FIXTURE_CUSTOM), encoding='utf-8')
            (root / 'core').mkdir()
            shutil.copy(STACK / 'core/poketr.js', root / 'core/poketr.js')
            (root / 'site').mkdir()
            shutil.copy(STACK / 'site/index.html', root / 'site/index.html')
            cache = root / '.cache/pokeapi.json'
            cache.parent.mkdir()
            cache.write_text(json.dumps({'source': 'test', 'entries': dictionary.parse_csvs(TABLES)}),
                             encoding='utf-8')
            version = json.loads((STACK / 'extension/manifest.json').read_text())['version']
            with patch.multiple(build, ROOT=root, EXTENSION=root / 'extension', CACHE=cache,
                                DIST=root / 'dist'), \
                    patch.object(dictionary, 'fetch_pokeapi', side_effect=AssertionError('no fetch')):
                build.build(release=version)
                first = (root / f'dist/poke-translate-site-v{version}.tar.gz').read_bytes()
                build.build(release=version)
                self.assertEqual((root / f'dist/poke-translate-site-v{version}.tar.gz').read_bytes(), first)
                with self.assertRaises(ValueError):
                    build.build(release='0.0.0-mismatch')
            site = root / 'dist/site'
            core = (STACK / 'core/poketr.js').read_bytes()
            self.assertEqual((site / 'poketr.js').read_bytes(), core)
            self.assertEqual((root / 'extension/poketr.js').read_bytes(), core)
            with zipfile.ZipFile(root / f'dist/poke-translate-extension-v{version}.zip') as archive:
                self.assertLessEqual({'manifest.json', 'background.js', 'poketr.js', 'dictionary.json'},
                                     set(archive.namelist()))
            with tarfile.open(root / f'dist/poke-translate-site-v{version}.tar.gz') as archive:
                self.assertEqual(sorted(archive.getnames()),
                                 ['dictionary.json', 'index.html', 'poke-translate-extension.zip', 'poketr.js'])
            built = json.loads((site / 'dictionary.json').read_text(encoding='utf-8'))
            self.assertIn('ガブ', built['entries']['species:445']['ja'])


if __name__ == '__main__':
    unittest.main()
