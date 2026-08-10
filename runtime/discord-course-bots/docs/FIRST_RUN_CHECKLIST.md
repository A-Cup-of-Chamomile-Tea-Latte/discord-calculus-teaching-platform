# First Run Checklist

## Developer Portal

- [ ] 建立 `course_assistant` Application 與 Bot。
- [ ] 建立 `dump_bot` Application 與 Bot。
- [ ] `course_assistant` 開啟 Members + Message Content intents。
- [ ] `dump_bot` 開啟 Message Content intent。
- [ ] 複製 Application IDs 至 `.env`。
- [ ] 產生 tokens 並只存入本機 `.env`。

## Discord test server

- [ ] 複製 Guild ID 至 `.env`。
- [ ] 執行 `make invite` 並加入兩隻 Bot。
- [ ] `course_assistant` Bot role 高於 `/lab bootstrap` 建立的學生角色。
- [ ] 不給任何一隻 Bot Administrator。

## First commands

- [ ] `make run-course`
- [ ] `/lab health`
- [ ] `/lab bootstrap`
- [ ] `/lab health`
- [ ] 建立 Forum 測試文章。
- [ ] 完成成案。
- [ ] 測試非原作者點擊。
- [ ] 測試關閉與重新詢問。
- [ ] `make probe-dump`
- [ ] 匯出該 thread。
