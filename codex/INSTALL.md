# Codex アダプタ — 導入

標準の導入方法は、リポジトリ直下の対話式インストーラである。

```sh
python install.py
```

導入先、Codex、研究プロファイルを順番に選び、変更計画を確認してから適用する。
非対話環境では次のように指定する。

```sh
python install.py --target ../my-research --adapter codex --profile general --yes
```

確認だけなら `--dry-run` を付ける。
既存の `STATE/` と `docs/` は上書きされず、任意STATE雛形は
`.research-ops/templates/` に保存される。
サブテーマ固有の結果や考察が別フォルダにある場合は、対話中に追加文書ルートとして入力する。
非対話形式では `--document-root individual --document-root population` のように繰り返し指定する。

以後、Codex 上で `$state-sync` `$state-audit` `$panel` として起動できる。

アダプタが使えない環境(素のチャット等)でも、各 `SKILL.md` の本文をコピーして貼れば動く
(OPERATIONS.md §5 階段0)。ロジックの正は常に `OPERATIONS.md`。

## 手動導入

インストーラを使えない場合は、その `--dry-run` 出力を配置一覧として使う。
最低限、汎用コア、選んだ `profiles/<name>/PROFILE.md`、`codex/skills/`、
`AGENTS.snippet.md` を導入する。`codex/skills/` の配置先は研究リポジトリの
`.agents/skills/` とする。

## 旧版からの移行

以前の `~/.codex/prompts/state-*.md` と `panel.md` はカスタムプロンプト方式の旧版であり、
スキルの動作確認後に削除できる。旧版は `/prompts:<name>` として見える場合があるため、
同名処理の混同を避けること。
