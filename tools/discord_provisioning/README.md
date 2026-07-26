# Discord provisioning dry-run

這個工具只 parse／validate declarative JSON、計算 current→desired diff、印出 dry-run 與
逆序 rollback plan。輸入必須 `fixtureOnly: true`，server name 與所有 resource key 必須有
明顯 fixture 前綴；`dump_bot` 不得取得 Administrator、Manage Roles、Manage Channels。

```bash
python -m tools.discord_provisioning \
  --current fixtures/provisioning/current-server.json \
  --desired fixtures/provisioning/desired-server.json
```

沒有 apply command、Discord SDK、HTTP adapter、token loader 或建立/刪除資源的程式碼。
輸出中的 `DELETE` 只是差異描述，不會執行。正式 roles、Private Support 與身份政策仍待決。
