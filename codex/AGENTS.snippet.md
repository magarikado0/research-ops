<!-- 研究リポジトリの AGENTS.md の末尾にこのブロックを追記する -->

## 研究運用(research-ops)

- 作業開始前に `STATE/README.md` と `RESEARCH_PROFILE.md` を読むこと。運用の正典は `OPERATIONS.md`。
- 3層(ログ → 登録済み文書ルート → STATE/)で文脈を管理する。詳細は文書ルートに全文、STATEは要約とリンク。
  矛盾時の信頼順位は ログ > 文書層 > STATE。
- 研究活動の区切りで完全版の同期案を作る(`$docs-sync`、既定dry-run)。
  続けてSTATEの同期案を作る(`$state-sync`、既定dry-run)。方向性の相談は `$panel`、
  月1で `$state-audit`。STATEへの適用と正式な意思決定は人間の明示承認後に行う。
- 詳細文書はその作業をした瞬間に書く。原則write-once、覆った結論にはerrataを一行追記する。
