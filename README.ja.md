# poke-translate

[English](README.md)

ポケモン用語を正しく訳す機械翻訳ツールです。ポケモン・わざ・とくせい・どうぐ・
タイプ・せいかく・ステータスを、翻訳エンジンへ送る前に**訳先言語の公式名**へ
固定します。「Earthquake」は「地震」ではなく「じしん」に、「じしん」は
「confidence（自信）」ではなく「Earthquake」になります。

**翻訳サイト**（静的ページ）と、Chrome系ブラウザ（Chrome・Edge・Brave・Vivaldi。
Android版Vivaldiを含む）の**拡張機能**の2つで使えます。どちらもブラウザの中だけで
動き、サーバ側の処理はありません。

```
Garchomp is a premier Stealth Rock setter. Earthquake is its main STAB move,
and Protect lets it scout. 252 Atk / 4 SpD / 252 Spe with a Jolly nature
allows it to 2HKO bulky Water-types. Its Psychic immunity is notable.

ガブリアスはプレミアステルスロック設置役です。じしんはメインのタイプ一致技であり、
まもるは偵察をさせます。 252こうげき/ 4とくぼう/ 252すばやさにようき性格を使用すると、
確定2発高耐久のみずタイプが可能になります。エスパー無効が注目に値します。
```
実際の出力（英→日）です。用語は固定されますが、その前後の文法は翻訳エンジンの
ままです。


## 仕組み

1. `core/poketr.js` が辞書で用語を探し（長い名前を優先）、`⟦1⟧` のような記号に
   置き換えます。
2. 置き換えた文を翻訳エンジンへ送ります。
3. 訳文の記号を訳先言語の公式名へ戻します。訳文から記号が落ちたときは警告します。

辞書は9言語（ja・en・ko・zh-TW・zh-CN・fr・de・es・it）に対応し、海外サイトの
書き方も理解します。

- `Landorus-Therian`・`Charizard-Mega-X` → ランドロス（れいじゅうフォルム）・メガリザードンＸ
- `Water-types`・`Tera Steel`・`Psychic immunity`（わざではなくタイプとして判別）
- `Atk / SpD / Spe`・`OHKO`・`2HKOed`・`STAB`・`EVs`・`wallbreaker`・`pivot`
- Showdown形式の型（`Garchomp @ Choice Scarf`・`Jolly Nature`・`- Earthquake`）は、
  機械翻訳せずに用語だけを置き換えます。

普通の単語と同じ名前（`Bold`・`Return`）は、文中で大文字始まりのときだけ用語と
みなします。ひらがな2文字の名前（「くさ」「みず」）は「くさタイプ」の形でだけ
拾うので、「くさい」には反応しません。

### 翻訳エンジン

既定では Google翻訳の**非公式**Webエンドポイント
（`translate.googleapis.com/translate_a/single`、`client=dict-chrome-ex`）を
ブラウザから直接呼びます。キーは不要ですが、公開されたAPIではないため、制限・
遮断・仕様変更がいつ起きてもおかしくなく、Googleの規約上すべての使い方が許される
とは限りません。段落はまとめて送り（1回あたり約3,500文字、同時に2件まで）、
通信回数を抑えています。別のエンジンを使うときは、`core/poketr.js` に
`translate(text, source, target)` を持つクラスを足します。

## 拡張機能

- ツールバーのボタン（または `Alt+T`）で、見ているページを訳します。訳文は各段落の
  下に入り、原文のリンクや書式はそのまま残ります。もう一度押すと「訳のみ」→
  「原文のみ」→「対訳」と切り替わります。
- スクロールで増える投稿や新しい返信も、自動で訳します。
- `<pre>`（Showdown形式の型など）は用語だけを置き換え、コードや入力欄には触れません。
- 権限は `activeTab`（ボタンを押したページだけ、押したときだけ）・`scripting`・
  `storage`・`contextMenus` と、`translate.googleapis.com` への通信だけです。

### 入れ方

[リリース](https://github.com/rurutheGeek/poke-translate/releases)から
`poke-translate-extension-vX.Y.Z.zip` を取って展開し、`chrome://extensions`
（Vivaldi は `vivaldi://extensions`）で**デベロッパーモード**を有効にして、
**パッケージ化されていない拡張機能を読み込む**で展開したフォルダを選びます。
訳先の言語は拡張機能の設定で変えられます（既定は日本語）。

## 翻訳サイト

`poke-translate-site-vX.Y.Z.tar.gz` は静的サイト一式（`index.html`・`poketr.js`・
`dictionary.json`・拡張機能のzip）です。任意の静的Webサーバで配信できます。
文章を貼って訳すほか、**用語だけ置き換え**にチェックすると、Showdown形式の型を
機械翻訳せずに変換できます。

## ビルド

Python 3.10以上（標準ライブラリのみ）。本体のテストには Node.js が要ります。

```bash
python3 build.py                    # dist/site/ と、読み込み用の extension/
python3 build.py --refresh          # PokéAPI から取り直す
python3 build.py --release 1.0.0    # dist/*.tar.gz と dist/*.zip も作る
python3 -m unittest discover -s tests
```

PokéAPI の版は `build.py` の `POKEAPI_REF` で固定し、取得結果は `.cache/` に
保存します。同じ入力からは、バイト単位で同じアーカイブができます。

## カスタム辞書

俗称・対戦用語・除外語は [`custom-terms.json`](custom-terms.json) に書きます。

```json
{"ref": "species:445", "ja": ["ガブ"]}
{"ja": ["S振り"], "en": ["Speed investment"]}
```

`ref` 付きは既存の用語に別名を足し、`ref` なしは新しい用語になります。各言語の
最初の名前が、その言語での訳語です。`ambiguous` は文頭では照合しない名前、
`exclude` は照合しない名前です。同じ表記が複数の用語にあるときは、カスタム >
ポケモン > わざ > とくせい > どうぐ > タイプ の順に採ります。

## リリース

`extension/manifest.json` の `version` と `CHANGELOG.md` を更新し、タグ `vX.Y.Z`
を push します。リリース用ワークフローがテスト・ビルドを行い、`SHA256SUMS` と
一緒に公開します。

## 出典と免責

- 公式名は [PokéAPI](https://github.com/PokeAPI/pokeapi) のデータを使っています。
- このプロジェクトは任天堂・クリーチャーズ・ゲームフリーク・株式会社ポケモン・
  Google とは関係がなく、承認や支援も受けていません。ポケモンおよびポケモンの名称は、
  各権利者の商標です。

## ライセンス

[MIT](LICENSE)
