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
→ DM case number, or record pending Email fallback
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

`dump_version` is not advanced by closing in this build because automatic verified export is not connected yet.

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
