# Portal Email controlled smoke

狀態：`PASS_LOCAL_REAL_PROVIDER / PRODUCTION_NOT_CONNECTED`

這個 runner 驗證 Portal backend 建立 challenge、SQLite durable outbox、GAS `MailApp`、人工輸入驗證碼、challenge consume 與 `PENDING_REVIEW` 申請建立。它使用 temporary SQLite，不連 Discord、不讀 production DB，也不等於 Portal rollout。

## 安全邊界

- 必須明示 `PORTAL_EMAIL_SMOKE=1`。
- 收件地址與預先核准的 SHA-256 fingerprint 必須一致；runner 不輸出地址或驗證碼。
- OAuth credential 必須是 regular file、非 symlink、mode `0600`，且包含 Sheets 與 `script.send_mail` scopes。
- SQLite、audit DB 與申請資料只存在 `TemporaryDirectory`；process 結束即刪除。
- 測試固定建立 Guest `PENDING_REVIEW` 申請，但不執行 Discord reviewer、role、nickname 或 DM mutation。
- PASS 前確認 outbox 的 destination／verification code 已清空、challenge 為 `CONSUMED`、audit 不含地址或驗證碼。

## 執行

所有值都從 process environment 注入，不寫入 repository：

```sh
export PORTAL_EMAIL_SMOKE=1
export PORTAL_EMAIL_SMOKE_DESTINATION='<明示核准的測試信箱>'
export PORTAL_EMAIL_SMOKE_DESTINATION_SHA256='<正規化地址的 SHA-256>'
export PORTAL_EMAIL_SMOKE_DISCORD_USERNAME='white.account'
export GAS_DEPLOYMENT_ID='<owner-only immutable deployment>'
export GOOGLE_OAUTH_CREDENTIALS='<mode-0600 dual-scope credential>'

node tools/run-python.mjs -m discord_course_bots.portal_email_smoke
```

收到信後只在 hidden prompt 輸入該次六位碼。成功輸出固定為：

```ini
portalEmailSmoke=PASS
emailDelivery=COMPLETED
emailChallenge=CONSUMED
joinApplication=PENDING_REVIEW
productionDatabaseModified=NO
discordMutation=NO
sensitiveValuesPrinted=NO
```

2026-08-28 已用明確核准的真實測試收件匣完成一次 PASS；repository 與文件不保存地址、驗證碼或截圖。
