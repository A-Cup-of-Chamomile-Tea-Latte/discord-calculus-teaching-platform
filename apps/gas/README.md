# Apps Script

Google Sheets 原型／行政 API 的 clasp-compatible 本機 scaffold。它不作高頻訊息資料庫、不保存原始 secrets，也**不是 Discord Gateway host**；Discord bots 必須在另一個可維持長連線的 Python runtime 執行。

## Local commands

```sh
npm run typecheck --workspace @calculus/gas
npm run test --workspace @calculus/gas
npm run build --workspace @calculus/gas
```

Build 使用 esbuild 將 `src/index.ts` bundle 為 `dist/Code.js`，公開 Apps Script 所需的全域 `doGet` / `doPost`，並複製 `appsscript.json`。所有 tests 都是 pure local logic，不需要 Google credential、clasp login 或 network。

Task 16 另公開 `bootstrapSheetsDryRun` 與 `bootstrapSheetsApply` operator functions；fixture mode會在任何 `SpreadsheetApp.openById` 前拒絕執行。Schema catalog與non-storage boundary見 `docs/SHEETS_SCHEMA.md`。

## Runtime configuration

正式 runtime 只從 Apps Script `PropertiesService.getScriptProperties()` 讀取：

- `FIXTURE_MODE`：未設定時安全預設 `true`；只接受 `true` / `false`。
- `APP_ENVIRONMENT`：未設定時為 `fixture`。
- `SPREADSHEET_ID`：fixture mode 不需要；切到 `false` 前必須提供。

不要把以上 runtime values 寫進 source、`.clasp.json` 或 repository。`.clasp.json.example` 只有 placeholder；真實 `.clasp.json` 已被 root `.gitignore` 排除。

## Routes

- `GET /`：fixture scaffold HTML 說明。
- `GET /health`：不含 secrets 的健康狀態，明確回報 `discordGatewayHost: false`。
- `POST /api/fixture/echo`：只在 fixture mode 接受 JSON object，只回報 key names，不保存或回傳 values。
- `GET /api/cases/lookup`、`GET /api/cases`：fixture public projection；Private Support排除。
- `POST /api/cases/refresh`：caller明確觸發的single `NO_OP` fixture，沒有polling。
- `POST /api/cases/follow-up`：不保存的`NOT_CONFIGURED` placeholder。
- 其他路徑：structured JSON 404。

GAS `ContentService` 無法直接設定任意 HTTP status；JSON response 以 `status` 欄位表達 application status。正式 API consumer 必須同時檢查 envelope，而不是只看 HTTP 200。

未來人工部署步驟與 owner/deployer 見 `docs/DEPLOYMENT_RUNBOOK.md`。本專案目前沒有 cloud project 或 deployment ID。

Case API contracts、provider ports、CORS/redirect與rate-limit策略見`docs/CASE_API.md`。

Task 18 的一次性「啟動碼」domain service、80-bit 強隨機格式、只存 fingerprint 的界線與 Google Sheets 併發限制見 `docs/ACTIVATION_CODES.md`。目前尚未提供 production repository 或公開兌換 route。

Task 19 的 provider-neutral 電子郵件驗證 service 只接記憶體 mock；六位 code、salted hash、expiry、attempt/send limit、cooldown、institutional/contact 分流及 Gmail/Apps Script quota 前提見 `docs/EMAIL_VERIFICATION.md`。目前不會寄送任何真實郵件。
