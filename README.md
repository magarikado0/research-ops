# research-ops

分野を問わず、研究をAIエージェントと一緒に長期運用するための**運用パッケージ**。
「プロジェクトの文脈を、常に最新かつ抜けなく保つ」ための3層ドキュメント体系と、
それを維持・活用する手続き(同期・監査・多視点審議)を、**ツール/モデル非依存**でまとめたもの。

## 考え方

- 正典は [`OPERATIONS.md`](OPERATIONS.md) 一つ。ツール名・モデル名を含まない純粋仕様。
- 各ツールのアダプタ(`claude-code/`, `codex/`)は、その正典を指すだけの薄いラッパ。
- だから **Claude Code でも Codex でも同じ運用**が回り、アダプタの無い環境でも
  プロンプトを手で渡せば動く(`OPERATIONS.md §5` の「呼び出しの階段」)。

## 3層(詳細は OPERATIONS.md)

```
ログ層(追記専用)     … 活動ログ・原記録・git。機械的事実。最強の正
文書層(完全版)      … 共有docs/と登録済みルート。網羅が正義。write-once
STATE/ 層(文脈パック) … 行動に必要な要約+リンク。鮮度が正義
```

## 4つの手続き

- **DOCS SYNC** … 活動ログ、原記録、git → 文書層。完全版を作る。既定はdry-run。
- **STATE SYNC** … 文書層 → STATE。現在の文脈を更新する。既定はdry-run。
- **AUDIT** … STATE だけで文脈が伝わるかを、隔離された読み手で実測。月1目安。
- **PANEL** … 方向性の多視点審議。独立ドラフト→相互反論→統合→人間の承認。

## 導入

研究リポジトリに対して、使うツールのアダプタの INSTALL を実行する:

- Claude Code → [`claude-code/INSTALL.md`](claude-code/INSTALL.md)
- Codex → [`codex/INSTALL.md`](codex/INSTALL.md)

両方入れてもよい(正典 `OPERATIONS.md` と `STATE/` は共有、アダプタだけ2つ置く)。
**最初は最小構成から**(`STATE/README.md` + `decisions.md` + `docs/README.md` + `research-ops.yml`)。
フォルダやファイルは、実際に必要になったときに雛形から足す(OPERATIONS.md §4)。

文書層は研究全体で一つとして扱うが、保存場所は複数登録できる。
共有文書を `docs/` に置き、サブテーマ固有の結果や考察を既存フォルダに残す構成にも対応する。

## 構成

```
research-ops/
├── OPERATIONS.md        # 正典(ツール/モデル非依存)
├── research-ops.template.yml # プロファイルと活動ログの設定
├── STATE.template/      # STATE/ の雛形(目的文入り)
├── docs.template/       # docs/ の説明
├── profiles/            # 分野別の語彙・STATE雛形・PANEL役割
├── install.py           # 対話・非対話インストーラ
├── claude-code/         # Claude Code アダプタ(skills + INSTALL)
└── codex/               # Codex アダプタ(skills + AGENTS.snippet + INSTALL)
```

## インストール

引数なしで起動すると、導入先、実行環境、研究プロファイルを対話形式で選べる。

```sh
python install.py
```

CIや自動化では引数を指定する。

```sh
python install.py --target ../my-research --adapter both --profile general --yes
```

既存のサブテーマフォルダを文書ルートとして登録する場合は、`--document-root` を繰り返す。

```sh
python install.py --target ../my-research --adapter both --profile machine-learning \
  --document-root individual --document-root population --yes
```

再実行時も研究固有のファイルは上書きしない。
選ばなかった既存アダプタは自動削除せず、削除手順は [`UPGRADING.md`](UPGRADING.md) に従う。

## 検証

Python 3.11以降で次を実行する:

```sh
python scripts/validate.py
```

Markdown参照、テンプレートの最小導入、アダプタ構造、正典との主要な整合性を検査する。
更新方法は [`UPGRADING.md`](UPGRADING.md)、変更履歴は [`CHANGELOG.md`](CHANGELOG.md) を参照。
