# BOT_OPEN_QUESTIONS — After First Live Test

| Item | Current test behavior | What live testing should decide |
|---|---|---|
| Reopen case number | Same thread and same case number | Confirm this remains final |
| Initial attachment storage | Metadata and Discord URL only | Decide when file bytes are downloaded |
| Private Support close | 48＋48 或手動結案後 48 小時，verified dump 後刪除 | Confirm white-account ACL and retention receipt |
| Case notification | Public／Private 都只用 Discord DM | Confirm DM failure manual-attention receipt |
| Identity sync | C01–C16／Guest roles 與持久暱稱已完成 | Confirm production mapping and reset test aliases to `001` |
| Draft timing | Configurable seconds | Observe whether 24h + 24h is operationally suitable |
| Forum starter availability | Five short fetch retries | Measure actual event timing and adjust retry strategy |
