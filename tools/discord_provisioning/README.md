# Discord infrastructure provisioning

這是目前唯一的 Discord server provisioning 入口。工具只接受 runtime `.env` 中
`TEST_GUILD_ID` 白名單內的 Guild，並使用 `course_assistant` token。

```bash
python -m tools.discord_provisioning inventory --guild-id <TEST_GUILD_ID>
python -m tools.discord_provisioning apply --guild-id <TEST_GUILD_ID> --reset-lab
python -m tools.discord_provisioning verify --guild-id <TEST_GUILD_ID>
```

永久 Private Support 入口必須走 targeted 路徑，不得為此重跑完整 `apply`：

```bash
python -m tools.discord_provisioning plan-private-entry --guild-id <TEST_GUILD_ID>
python -m tools.discord_provisioning ensure-private-entry --guild-id <TEST_GUILD_ID>
```

`plan-private-entry` 只保存 inventory／plan，Discord mutation 固定為 `false`。
`ensure-private-entry` 只採用或建立 `channel.private_support_entry`、校正該頻道的 parent、topic
與 ACL，再寫入 `private_support_entry_channel_id`。使用方式直接寫在 topic，頻道本身禁止一般訊息。
其他 mapping drift 只列入結果，
不修改 role、category、forum、其他頻道或全域 Bot boundary；必要 dependency 缺漏時直接停止。

`apply` 會保存結構 inventory、清除已核准舊資源、依 logical key 建立或校正資源、
保存 Discord IDs、建立 welcome／guidelines 內容並執行 live verify。詳細操作紀錄、
inventory 與 verify JSON 位於：

```text
.local/discord-course-bots-runtime/artifacts/provisioning/
```

固定 resource mapping 位於：

```text
.local/discord-course-bots-runtime/data/discord_provisioning_resources.json
```

入口 rollback mapping 固定為：只有本次 operation log 明確記錄為 `created` 時才可刪入口；
既有 `category.private_support` 與所有動態案件頻道一律保留。若入口原本已存在並被 adopted，
rollback 只能依 `inventory-before.json` 還原該入口的 parent、topic 與 ACL，不得刪除。

舊 fixture-only planner、NAP 模擬入口與 provisioning fixtures 已由 live CLI 取代並移除。
