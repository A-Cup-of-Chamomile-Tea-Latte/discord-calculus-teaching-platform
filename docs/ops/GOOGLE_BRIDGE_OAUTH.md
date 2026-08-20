# Google Bridge OAuth

> 2026-08-20 現況：本機 Bridge 授權與 `scripts.run` 已可用，但 Google Auth Platform 仍是
> External／Testing。因 token 含 Sheets scope，目前 refresh token 通常只有 7 天測試生命週期，
> 不得把它稱為長期 production credential。

## 為什麼分兩種授權

- `clasp` 只負責把受管 GAS source 推到兩個既有專案。
- 24h bridge 使用獨立、可刷新、可撤銷的 authorized-user credential 呼叫 `scripts.run`；不讀 `.clasprc.json`。

Standalone GAS 與 OAuth client 必須隸屬同一個 standard Google Cloud project，且啟用 Apps Script API。Local bridge 只申請：

```text
https://www.googleapis.com/auth/spreadsheets
```

寄信與 trigger 權限只存在 bound GAS，不進 local bridge token。

## 建立與更新

```bash
discord-google-oauth-bootstrap \
  --client-secrets /secure/path/oauth-client.json \
  --output /secure/path/google-oauth.json
chmod 0600 /secure/path/google-oauth.json
```

只在 Chrome「Ding Ding」使用專案帳號完成授權。不要把瀏覽器回傳碼、client secret、refresh token 或帳號貼進聊天與報告。

完成後以安全傳輸安裝到：

```text
/etc/calculus-discord/google-oauth.json
```

bridge 只讀此檔，access token 在記憶體刷新。撤銷後 bridge 轉為 degraded、queue 留在 SQLite，Discord 仍運作。

## 上線前人工 gate

在 24h production observation 前，由專案 owner 在 Google Auth Platform 二選一：

1. 將 OAuth consent publishing status 切到 Production，處理 Google 畫面要求的驗證，再用
   Chrome「Ding Ding」重新授權一次；或
2. 明確接受 Testing 模式，並把約每 7 天重新授權列為人工維運工作。

官方規則見 [Google OAuth 2.0 refresh token expiration](https://developers.google.com/identity/protocols/oauth2#expiration)。
切換 publishing status 不等於放寬 GAS access；standalone deployment 仍必須維持 owner-only，
scope 仍只允許 Sheets。
