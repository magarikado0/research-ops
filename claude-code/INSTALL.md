# Claude Code アダプタ — 導入

標準の導入方法は、リポジトリ直下の対話式インストーラである。

```sh
python install.py
```

導入先、Claude Code、研究プロファイルを順番に選び、変更計画を確認してから適用する。
非対話環境では次のように指定する。

```sh
python install.py --target ../my-research --adapter claude-code --profile general --yes
```

確認だけなら `--dry-run` を付ける。
既存の `STATE/` と `docs/` は上書きされず、任意STATE雛形は
`.research-ops/templates/` に保存される。
サブテーマ固有の結果や考察が別フォルダにある場合は、対話中に追加文書ルートとして入力する。
非対話形式では `--document-root individual --document-root population` のように繰り返し指定する。

以後、`/state-sync` `/state-audit` `/panel` で起動できる。ロジックの正は常に `OPERATIONS.md`。

## 手動導入

インストーラを使えない場合は、その `--dry-run` 出力を配置一覧として使う。
最低限、汎用コア、選んだ `profiles/<name>/PROFILE.md`、`claude-code/skills/`、
`CLAUDE.snippet.md` を導入する。

Stopフックや日次タスクを追加する場合も、SYNCはdry-runのまま実行する。
