---
name: docs-sync
description: 活動ログ、原記録、git差分から、登録済み文書ルートへ完全版の記録を作る。研究活動の直後やSTATE同期の前に使う。
---

# docs-sync

リポジトリ直下の `OPERATIONS.md` をすべて読み、その **§3(二段階の蒸留)と
§6(DOCS SYNC手続き)** に厳密に従う。

- `last_docs_sync_commit`、`activity_log_cursors`、`document_roots`、`activity_logs` を先に検証する。
- 前回カーソル以後のgit差分、未コミット差分、活動ログ、原記録だけを対象にする。
- 文書層とSTATEの派生差分をground truthとして二重処理しない。
- 事実のscopeに対応する文書ルートを選ぶ。保存先が曖昧なら候補を提示して人間の選択を待つ。
- 新しい活動は原則として新規文書へ記録する。既存文書の変更は継続更新対象、追記、errataに限る。
- 共有文書とサブテーマ文書へ同じ詳細を重複記録しない。
- 既定はdry-run。対象ログ、保存先、文書diffを提示し、明示承認後だけ適用する。
- 適用成功後に限り、DOCS SYNC用カーソルを進める。
