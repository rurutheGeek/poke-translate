# poke-translate

[日本語](README.ja.md)

Machine translation that keeps Pokémon terms right. Pokémon, moves, abilities,
items, types, natures and stats are replaced with their **official names in the
target language** before the text goes to the translation engine, so
"Earthquake" becomes 「じしん」 instead of 「地震」, and 「じしん」 becomes
"Earthquake" instead of "confidence".

It comes as a **static translation site** and a **browser extension** for
Chromium-based browsers (Chrome, Edge, Brave, Vivaldi — including Vivaldi for
Android). Both run entirely in the browser; there is no server-side processing.

```
Garchomp is a premier Stealth Rock setter. Earthquake is its main STAB move,
and Protect lets it scout. 252 Atk / 4 SpD / 252 Spe with a Jolly nature
allows it to 2HKO bulky Water-types. Its Psychic immunity is notable.

ガブリアスはプレミアステルスロック設置役です。じしんはメインのタイプ一致技であり、
まもるは偵察をさせます。 252こうげき/ 4とくぼう/ 252すばやさにようき性格を使用すると、
確定2発高耐久のみずタイプが可能になります。エスパー無効が注目に値します。
```
Actual output (en → ja). Terms are fixed; the grammar around them is still
the engine's.


## How it works

1. `core/poketr.js` finds terms with a dictionary (longest match first) and
   replaces them with placeholders such as `⟦1⟧`.
2. The text is sent to the translation engine.
3. The placeholders in the translation are replaced with the official names in
   the target language. Missing placeholders are reported as warnings.

The dictionary covers nine languages (ja, en, ko, zh-TW, zh-CN, fr, de, es, it)
and also understands notation used on overseas sites:

- `Landorus-Therian`, `Charizard-Mega-X` → ランドロス（れいじゅうフォルム）, メガリザードンＸ
- `Water-types`, `Tera Steel`, `Psychic immunity` (a type, not the move)
- `Atk / SpD / Spe`, `OHKO`, `2HKOed`, `STAB`, `EVs`, `wallbreaker`, `pivot`
- Showdown sets (`Garchomp @ Choice Scarf`, `Jolly Nature`, `- Earthquake`) are
  converted term by term without machine translation.

Names that are also ordinary words (`Bold`, `Return`) are only treated as terms
when they are capitalised inside a sentence, and two-letter hiragana names
(「くさ」「みず」) only as part of 「くさタイプ」 so that 「くさい」 is left alone.

### Translation engine

The default engine is Google Translate's **unofficial** web endpoint
(`translate.googleapis.com/translate_a/single`, `client=dict-chrome-ex`), called
directly from the browser. It needs no key, but it is not a documented API: it
may be rate-limited, blocked or changed at any time, and its use may not be
permitted by Google's terms in every situation. Paragraphs are batched (about
3,500 characters per request, at most two requests at a time) to keep the number
of requests low. To use another engine, add a class with
`translate(text, source, target)` to `core/poketr.js`.

## Browser extension

- Click the toolbar button (or press `Alt+T`) to translate the current page.
  Translations appear under each paragraph; links and formatting of the original
  are untouched. Click again to switch between bilingual, translation only and
  original only.
- Content added later (infinite scroll, new replies) is translated automatically.
- `<pre>` blocks such as Showdown sets get term replacement only. Code and input
  fields are never touched.
- Permissions: `activeTab` (the page you click on, only then), `scripting`,
  `storage`, `contextMenus`, and network access to `translate.googleapis.com`
  only.

### Install

Download `poke-translate-extension-vX.Y.Z.zip` from the
[releases](https://github.com/rurutheGeek/poke-translate/releases), extract it,
open `chrome://extensions` (`vivaldi://extensions` in Vivaldi), turn on
**Developer mode** and choose **Load unpacked** with the extracted folder.
The target language is set in the extension options (Japanese by default).

## Translation site

`poke-translate-site-vX.Y.Z.tar.gz` contains a static site (`index.html`,
`poketr.js`, `dictionary.json` and the extension zip). Serve it from any static
web server. Paste text and translate, or tick **terms only** to convert a
Showdown set without machine translation.

## Build

Requires Python 3.10+ (standard library only). Node.js is needed for the core
tests.

```bash
python3 build.py                    # dist/site/ and the unpacked extension/
python3 build.py --refresh          # download PokéAPI again
python3 build.py --release 1.0.0    # also dist/*.tar.gz and dist/*.zip
python3 -m unittest discover -s tests
```

The PokéAPI commit is pinned in `build.py` (`POKEAPI_REF`), and the download is
cached in `.cache/`. Builds are reproducible: the same inputs give byte-for-byte
identical archives.

## Custom terms

Nicknames, battle slang and exclusions live in
[`custom-terms.json`](custom-terms.json):

```json
{"ref": "species:445", "ja": ["ガブ"]}
{"ja": ["S振り"], "en": ["Speed investment"]}
```

An entry with `ref` adds aliases to an existing term; one without `ref` is a new
term. The first name for each language is the one used in translations.
`ambiguous` lists names that are not matched at the start of a sentence, and
`exclude` lists names that are never matched. When the same text belongs to
several terms, custom terms win, then Pokémon, moves, abilities, items and types.

## Releasing

Update `version` in `extension/manifest.json` and `CHANGELOG.md`, then push a
tag `vX.Y.Z`. The release workflow runs the tests, builds the archives and
publishes them with `SHA256SUMS`.

## Credits and disclaimer

- Official names come from [PokéAPI](https://github.com/PokeAPI/pokeapi).
- This project is not affiliated with, endorsed or sponsored by Nintendo,
  Creatures Inc., GAME FREAK inc., The Pokémon Company or Google. Pokémon and
  Pokémon names are trademarks of their respective owners.

## License

[MIT](LICENSE)
