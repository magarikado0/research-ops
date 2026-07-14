# Claude Code アダプタ — 導入

研究リポジトリに対して、一度だけ以下を行う(手作業 or エージェントに依頼)。

1. `OPERATIONS.md` を研究リポジトリの直下にコピーする。
2. `STATE.template/` の中身を研究リポジトリの `STATE/` にコピーする。
   ただし **最初は `README.md` と `decisions.md` だけを残す**(OPERATIONS.md §4 最小から)。
   `motivation.md` 等は必要になったときに雛形から足す。
3. `docs.template/README.md` を `docs/README.md` にコピーする(サブフォルダは書くものが出たとき作る)。
4. この `skills/` 配下を研究リポジトリの `.claude/skills/` にコピーする。
5. 研究リポジトリの `CLAUDE.md` に次を追記する:

   ```
   ## 研究運用
   - 作業開始前に STATE/README.md を読むこと。運用の正典は OPERATIONS.md。
   - 区切りで /state-sync、方向性の相談は /panel、月1で /state-audit。
   ```

6. (任意)セッション終了時に未同期なら同期を促すフックを `.claude/settings.json` の Stop フックに追加する。
7. (任意)日次照合を scheduled task として登録する(/state-sync を1日1回)。

以後、`/state-sync` `/state-audit` `/panel` で起動できる。ロジックの正は常に `OPERATIONS.md`。
