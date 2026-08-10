# Discord infrastructure provisioning

這是目前唯一的 Discord server provisioning 入口。工具只接受 runtime `.env` 中
`TEST_GUILD_ID` 白名單內的 Guild，並使用 `course_assistant` token。

```bash
python -m tools.discord_provisioning inventory --guild-id <TEST_GUILD_ID>
python -m tools.discord_provisioning apply --guild-id <TEST_GUILD_ID> --reset-lab
python -m tools.discord_provisioning verify --guild-id <TEST_GUILD_ID>
```

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

舊 fixture-only planner、NAP 模擬入口與 provisioning fixtures 已由 live CLI 取代並移除。
