# Google Bridge OAuth

> 2026-08-20 現況：Google Auth Platform 已是 External／Production，且 consent config 只登記
> Sheets scope。新的 Production credential 已在本機以 owner 帳號完成授權與 refresh 驗證，
> 並維持 `0600`；remote owner-only staging refresh 也已通過，尚未安裝成 production secret。

## 為什麼分兩種授權

- `clasp` 只負責把受管 GAS source 推到兩個既有專案。
- 24h bridge 使用獨立、可刷新、可撤銷的 authorized-user credential 呼叫 `scripts.run`；不讀 `.clasprc.json`。

Standalone GAS 與 OAuth client 必須隸屬同一個 standard Google Cloud project，且啟用 Apps Script API。Local bridge 只申請：

```text
https://www.googleapis.com/auth/spreadsheets
```

寄信與 trigger 權限只存在 bound GAS，不進 local bridge token。

## 固定資料邊界

Google 的 Sheets scope 在 OAuth 層無法限制到某個 Drive 資料夾，因此 runtime 必須維持更窄的
應用層邊界：

- 只呼叫既有 owner-only Apps Script deployment。
- GAS 只開啟 Script Properties 中明確設定的單一 `BRIDGE_SPREADSHEET_ID`，並核對
  `BRIDGE_SPREADSHEET_FINGERPRINT`。
- 不列舉、搜尋、掃描或開啟其他 Drive／Sheets 檔案，也不遍歷該帳號的資料夾。
- 不以除錯、盤點或方便為由新增 Drive-wide scope；任何 target 或 scope 擴張都必須先取得使用者明示。
- 文件、log 與交接只記錄 safe result，不輸出其他檔案名稱、內容或識別碼。

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

在 24h production observation 前，專案 owner 必須在 Production 狀態用「Ding Ding」專案帳號
重新授權一次，產生新的長期 credential。重新授權前後都必須維持上方的單一 Spreadsheet
ID／fingerprint 邊界；不得藉 OAuth 流程探索其他 Drive／Sheets 資料。

官方規則見 [Google OAuth 2.0 refresh token expiration](https://developers.google.com/identity/protocols/oauth2#expiration)。
切換 publishing status 不等於放寬 GAS access；standalone deployment 仍必須維持 owner-only，
scope 仍只允許 Sheets。
