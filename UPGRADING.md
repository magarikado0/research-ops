# 更新手順

research-opsは研究リポジトリへ必要なファイルをコピーして使う。
更新時は対象リポジトリの未コミット変更を確認し、インストーラを再実行する。

1. [`CHANGELOG.md`](CHANGELOG.md) で破壊的変更を確認する。
2. `python install.py --target <研究リポジトリ> --adapter <環境> --profile <プロファイル> --dry-run`
   で変更計画を確認する。
3. 対話形式で競合を処理するか、`--conflict skip|backup|overwrite` を明示して再実行する。
4. `STATE/` と `docs/` はインストーラも上書きしない。新しい任意雛形は
   `.research-ops/templates/` から必要なものだけ手で追加する。
5. `python <研究リポジトリ>/.research-ops/validate.py --target <研究リポジトリ>` を実行する。
6. DOCS SYNC、STATE SYNC、AUDITをそれぞれdry-runし、結果を人間が確認する。

## 1.xから2.0への移行

- `~/.codex/prompts/` の旧プロンプトは、`.agents/skills/` 版の動作確認後に削除する。
- `STATE/README.md` 冒頭へSTATE SYNC用とDOCS SYNC用のカーソルを追加する。
  旧 `last_sync_*` は `last_state_sync_*` へ、旧 `experiment_log_cursors` は
  `activity_log_cursors` へインストーラが名称を移行する。
- `research-ops.yml` の旧 `experiment_logs` は `activity_logs` へ移行し、研究プロファイルを選ぶ。
- 完全版の文書が `docs/` 以外にもある場合は、各保存場所を `document_roots` に登録する。
  未設定の既存リポジトリには、インストーラが共有 `docs/` を既定ルートとして追加する。
- READMEの目次から、まだ存在しないSTATEファイルを削除する。
- 未承認のPANEL結果が `decisions.md` にある場合、審議記録へ移すか、未承認である旨を追記する。

## 削除

アダプタだけを外す場合は、導入時に追加したskillsとAGENTS/CLAUDEの追記部分を削除する。
`STATE/`、`docs/`、活動ログ、`decisions.md` は研究記録なので、research-opsを使わなくなっても
自動削除しない。
