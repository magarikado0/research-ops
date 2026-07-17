---
name: state-sync
description: STATE/ を git、登録済み活動ログ、複数の文書ルートと照合し、同期差分を提案または承認後に適用する。研究作業の区切りやセッション終了時に使う。
---

# state-sync

リポジトリ直下の `OPERATIONS.md` をすべて読み、特に §3 と §6 に厳密に従う。

- `STATE/README.md` の同期カーソルと `research-ops.yml` の `document_roots`、`activity_logs` を先に検証する。
- `last_sync_commit..HEAD`、未コミット差分、登録済み活動ログのカーソル以後だけを照合する。
- 登録されたすべての文書ルートを一つの文書層として照合する。ルート間で同じ詳細を複製しない。
- 記憶や会話上の自己申告を ground truth にしない。
- 古くなったSTATEの削除と沈殿、READMEの目次腐敗チェックも同期に含める。
- `STATE/decisions.md` の既存部分は変更しない。
- 既定はdry-run。まずdiff案と根拠を提示し、ユーザーが明示的に適用を指示した場合だけ更新する。
- 適用成功後に限り、コミットSHA、タイムゾーン付き時刻、活動ログ位置のカーソルを進める。
