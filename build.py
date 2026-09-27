#!/usr/bin/env python3
"""Build the dictionary, the static site and the browser extension.

    python3 build.py                     # dist/site/ and extension/ (load unpacked)
    python3 build.py --refresh           # download the official names again
    python3 build.py --release 1.2.0     # also dist/*.tar.gz and dist/*.zip

The PokéAPI download is cached in ``.cache/pokeapi.json`` and kept until
``--refresh``, so rebuilding never changes official names silently;
``custom-terms.json`` is applied on every build.  Outputs are byte-for-byte
reproducible from the same inputs.
"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import zipfile

import dictionary

ROOT = Path(__file__).resolve().parent
EXTENSION = ROOT / 'extension'
CACHE = ROOT / '.cache/pokeapi.json'
DIST = ROOT / 'dist'
ZIP_NAME = 'poke-translate-extension.zip'
# The PokéAPI commit the official names come from. Bump it and build --refresh.
POKEAPI_REF = '168b1e89467054cda2e7df43ccebbb69b459497a'
FIXED_TIME = (2026, 1, 1, 0, 0, 0)


def write(path, data):
    """Replace ``path`` only when its content changes; return whether it did."""
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_bytes(data)
    temporary.chmod(0o644)
    temporary.replace(path)
    return True


def extension_zip():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(EXTENSION.iterdir()):
            if path.is_file() and not path.name.endswith('.tmp'):
                info = zipfile.ZipInfo(path.name, date_time=FIXED_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, path.read_bytes())
    return buffer.getvalue()


def site_tarball(site):
    buffer = io.BytesIO()
    # mtime=0 keeps the gzip header, and so the checksum, stable between builds.
    with gzip.GzipFile(fileobj=buffer, mode='wb', mtime=0) as compressed, \
            tarfile.open(fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT) as archive:
        for path in sorted(site.iterdir()):
            data = path.read_bytes()
            info = tarfile.TarInfo(path.name)
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def build(refresh=False, ref=POKEAPI_REF, release=None):
    manifest = json.loads((EXTENSION / 'manifest.json').read_text(encoding='utf-8'))
    if release and release != manifest['version']:
        raise ValueError(f'release {release} does not match extension/manifest.json {manifest["version"]}')
    if refresh or not CACHE.exists():
        base = dictionary.fetch_pokeapi(ref)
        write(CACHE, json.dumps(base, ensure_ascii=False).encode('utf-8'))
        print(f'CHANGED: {len(base["entries"])} official terms from {base["source"]}')
    base = json.loads(CACHE.read_text(encoding='utf-8'))
    custom = json.loads((ROOT / 'custom-terms.json').read_text(encoding='utf-8'))
    built = json.dumps(dictionary.build(base, custom), ensure_ascii=False,
                       separators=(',', ':')).encode('utf-8')
    core = (ROOT / 'core/poketr.js').read_bytes()

    changed = [write(EXTENSION / name, data)
               for name, data in [('poketr.js', core), ('dictionary.json', built)]]
    site = DIST / 'site'
    changed += [write(site / name, data)
                for name, data in [('index.html', (ROOT / 'site/index.html').read_bytes()),
                                   ('poketr.js', core), ('dictionary.json', built)]]
    # Phones load the extension from a zip, so the site hands out the same files.
    changed.append(write(site / ZIP_NAME, extension_zip()))
    digest = hashlib.sha256(built).hexdigest()[:12]
    print(f'{"CHANGED" if any(changed) else "OK"}: site and extension built (dictionary {digest})')

    if release:
        for name, data in [(f'poke-translate-site-v{release}.tar.gz', site_tarball(site)),
                           (f'poke-translate-extension-v{release}.zip', extension_zip())]:
            write(DIST / name, data)
            print(f'{hashlib.sha256(data).hexdigest()}  {name}')


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--refresh', action='store_true', help='download PokéAPI again')
    parser.add_argument('--ref', default=POKEAPI_REF, help='PokéAPI commit')
    parser.add_argument('--release', metavar='VERSION', help='also write release archives')
    args = parser.parse_args()
    build(args.refresh, args.ref, args.release)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
