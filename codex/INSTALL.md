# Codex アダプタ — 導入

研究リポジトリに対して、一度だけ以下を行う。

1. `OPERATIONS.md` を研究リポジトリの直下にコピーする。
2. `STATE.template/` の中身を `STATE/` にコピーする。
   ただし **最初は `README.md` と `decisions.md` だけを残す**(OPERATIONS.md §4 最小から)。
3. `docs.template/README.md` を `docs/README.md` にコピーする。
4. 研究リポジトリ直下の `AGENTS.md` に `AGENTS.snippet.md` の内容を追記する
   (AGENTS.md が無ければ新規作成)。
5. この `prompts/` の各ファイルを Codex のプロンプト置き場に置く:
   - ユーザー全体で使うなら `~/.codex/prompts/`(確実)。
   - プロジェクト単位で使いたい場合は、お使いの Codex がプロジェクトプロンプト
     (例: リポジトリの `.codex/prompts/`)に対応していればそこへ。未対応なら `~/.codex/prompts/` を使う。
   - ファイル名がそのままコマンド名になる(`state-sync.md` → `/state-sync`)。

以後、Codex 上で `/state-sync` `/state-audit` `/panel` として起動できる。

アダプタが使えない環境(素のチャット等)でも、`prompts/*.md` の中身をコピーして貼れば動く
(OPERATIONS.md §5 階段0)。ロジックの正は常に `OPERATIONS.md`。
