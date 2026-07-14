<!-- 研究リポジトリの AGENTS.md の末尾にこのブロックを追記する -->

## 研究運用(research-ops)

- 作業開始前に `STATE/README.md` を読むこと。運用の正典は `OPERATIONS.md`。
- 3層(ログ → docs/ → STATE/)で文脈を管理する。詳細は docs に全文、STATE は要約+リンク。
  矛盾時の信頼順位は ログ > docs > STATE。
- 作業の区切りで STATE を同期する(`/state-sync`)。方向性の相談は `/panel`、月1で `/state-audit`。
- docs はその作業をした瞬間に書く(docs ファースト)。原則 write-once、覆った結論には errata 一行を追記。
