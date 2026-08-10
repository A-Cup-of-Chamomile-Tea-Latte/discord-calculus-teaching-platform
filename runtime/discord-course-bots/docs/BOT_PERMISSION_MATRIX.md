# Bot Permission Matrix — Test Guild v0.1

| Permission | course_assistant | dump_bot | Test purpose |
|---|---:|---:|---|
| View Channels | ✅ | ✅ | 指定測試頻道／匯出 |
| Send Messages | ✅ | ❌ | 設定訊息與狀態 |
| Send Messages in Threads | ✅ | ❌ | Forum 案件互動 |
| Read Message History | ✅ | ✅ | 校正／匯出 |
| Embed Links | ✅ | ❌ | 健康檢查與狀態訊息 |
| Attach Files | ✅ | ❌ | 後續 Portal／私人附件測試 |
| Manage Threads | ✅ | ❌ | 標題、封存、重開、刪除草稿 |
| Manage Nicknames | ✅ | ❌ | 後續 identity_sync |
| Manage Roles | ✅ | ❌ | 測試 Student／Guest 角色 |
| Manage Channels | ✅ | ❌ | Private Support 暫時頻道 |
| Administrator | ❌ | ❌ | 禁止 |
| Manage Guild | ❌ | ❌ | 不需要 |
| Kick/Ban Members | ❌ | ❌ | 不需要 |
| Manage Webhooks | ❌ | ❌ | 不需要 |
| Mention Everyone | ❌ | ❌ | 不需要 |

程式另加三層限制：

1. 單一 `TEST_GUILD_ID`。
2. `/lab bootstrap` 與管理命令的 owner allowlist。
3. SQLite runtime config 記錄可操作 Forum、Private Support category 與角色 ID。
