# Google Bridge OAuth

## 為什麼分兩種授權

- `clasp` 只負責把受管 GAS source 推到兩個既有專案。
- 24h bridge 使用獨立、可刷新、可撤銷的 authorized-user credential 呼叫 `scripts.run`；不讀 `.clasprc.json`。

Standalone GAS 與 OAuth client 必須隸屬同一個 standard Google Cloud project，且啟用 Apps Script API。Local bridge 只申請：

```text
https://www.googleapis.com/auth/spreadsheets
```

寄信與 trigger 權限只存在 bound GAS，不進 local bridge token。

## 一次性建立

```bash
discord-google-oauth-bootstrap \
  --client-secrets /secure/path/oauth-client.json \
  --output /secure/path/google-oauth.json
chmod 0600 /secure/path/google-oauth.json
```

只在 Chrome「Ding Ding」登入 `ntusupercool@gmail.com`。不要把瀏覽器回傳碼、client secret、refresh token 貼進聊天。

完成後以安全傳輸安裝到：

```text
/etc/calculus-discord/google-oauth.json
```

bridge 只讀此檔，access token 在記憶體刷新。撤銷後 bridge 轉為 degraded、queue 留在 SQLite，Discord 仍運作。
