# BOT_DATA_FLOW — Implemented Test Slice

## Public Forum

```text
User creates post in configured Forum
→ on_thread_create
→ fetch starter message
→ create minimal draft row
→ send public setup controls
→ original author enters keyword
→ original author selects AI Yes/No
→ validate keyword
→ rename thread with system prefix
→ save initial snapshot + case row
→ delete setup message
→ enqueue Discord DM with case number; failure enters manual attention
```

## Close and reopen

```text
Staff runs /case close
→ case becomes CLOSED
→ closure message + persistent Reopen button
→ archive thread

Original author clicks Reopen
→ case becomes TRACKED
→ reopen_count += 1
→ unarchive thread
→ append cycle suffix 2/3/...
```

`dump_version` is not advanced by closing in this build. Private Support 使用獨立的可靠 job
狀態；公開案件的版本化 dump 仍是明確操作。

## dump_bot

```text
Local administrator runs probe/export
→ connect only to TEST_GUILD_ID
→ verify channel read permissions
→ fetch history oldest-first
→ write JSON + Markdown
→ write SHA-256 manifest
→ disconnect
```

Private Support 的 online worker 只處理已由授權操作建立的本機 job：

```text
auto-closed Private Support, or manually closed for 48 hours, is queued
→ one worker atomically claims it with a unique token and expiring lease
→ heartbeat renews the live claim during export
→ fetch registered closed channel and write files
→ verify manifest and hashes
→ token-checked transition to VERIFIED
→ delete only after VERIFIED; otherwise retain the channel for manual attention
```

暫時性失敗會清除 claim、設定 bounded exponential backoff 並回到 `PENDING`；永久錯誤或
第五次失敗進入 `FAILED`。資料庫只保存固定 error code，不保存原始 exception。逾時 lease
可被其他 worker 接手，舊 token 不得完成新 claim。
