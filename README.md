# research-ops

機械学習の予測研究を、AIエージェントと一緒に長期運用するための**運用パッケージ**。
「プロジェクトの文脈を、常に最新かつ抜けなく保つ」ための3層ドキュメント体系と、
それを維持・活用する手続き(同期・監査・多視点審議)を、**ツール/モデル非依存**でまとめたもの。

## 考え方

- 正典は [`OPERATIONS.md`](OPERATIONS.md) 一つ。ツール名・モデル名を含まない純粋仕様。
- 各ツールのアダプタ(`claude-code/`, `codex/`)は、その正典を指すだけの薄いラッパ。
- だから **Claude Code でも Codex でも同じ運用**が回り、アダプタの無い環境でも
  プロンプトを手で渡せば動く(`OPERATIONS.md §5` の「呼び出しの階段」)。

## 3層(詳細は OPERATIONS.md)

```
ログ層(追記専用)     … 実験ログ・git。機械的事実。最強の正
docs/ 層(完全版)     … 細部まで抜けない記録。網羅が正義。write-once
STATE/ 層(文脈パック) … 行動に必要な要約+リンク。鮮度が正義
```

## 3つの手続き

- **SYNC**(`/state-sync`) … docs → STATE の一方向蒸留。区切り/セッション終了時。
- **AUDIT**(`/state-audit`) … STATE だけで文脈が伝わるかの実測。月1目安。
- **PANEL**(`/panel`) … 方向性の多視点審議。独立ドラフト→相互反論→統合。

## 導入

研究リポジトリに対して、使うツールのアダプタの INSTALL を実行する:

- Claude Code → [`claude-code/INSTALL.md`](claude-code/INSTALL.md)
- Codex → [`codex/INSTALL.md`](codex/INSTALL.md)

両方入れてもよい(正典 `OPERATIONS.md` と `STATE/` は共有、アダプタだけ2つ置く)。
**最初は最小構成から**(`STATE/README.md` + `decisions.md` + 実験ログ)。
フォルダやファイルは、実際に必要になったときに雛形から足す(OPERATIONS.md §4)。

## 構成

```
research-ops/
├── OPERATIONS.md        # 正典(ツール/モデル非依存)
├── STATE.template/      # STATE/ の雛形(目的文入り)
├── docs.template/       # docs/ の説明
├── claude-code/         # Claude Code アダプタ(skills + INSTALL)
└── codex/               # Codex アダプタ(prompts + AGENTS.snippet + INSTALL)
```
