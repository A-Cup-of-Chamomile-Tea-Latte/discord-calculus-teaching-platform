# 契約版本與相容性規則

## 版本模型

- 每筆 record 都必須有 `schemaVersion`；目前 major/minor 為 `1.0`。
- 同一 major 內，只能新增 optional 欄位、放寬非安全限制或加入不改變既有語意的文件。
- 移除／改名 required 欄位、改變欄位語意或型別、收窄既有有效值，必須提升 major，提供 migration 與並行讀取期。
- Enum 新值對不認識它的消費者通常是 breaking change；除非所有消費者先部署 tolerant-reader，否則視為 major change。案件狀態另須 ADR。

## IDs 與顯示標籤

- `*Id` 是 opaque、穩定、只供關聯的字串；不得從顯示名稱推導，也不得在 UI 當作友善標籤。
- `caseNumber`、`displayLabel`、`courseAlias` 是顯示／操作標籤，可依政策調整；它們不取代內部 ID。
- Discord snowflake 以字串保存，避免 JavaScript 整數精度問題。

## 預設與投影

- 安全相關預設必須在 record 中明寫，不依賴 validator 自動補值。
- Legacy v1 `Case`、`ExportManifest` 仍將 Private Support 匯出強制為 `EXCLUDED`；這是匯出的 fail-closed 相容邊界，不會覆寫 Bot 保存的逐案 AI 選擇。
- 舊 `CaseLookupResponse` 只供 legacy GAS／fixture 相容。當前 `CaseStatusLookupResponse` 可對 GENERAL 與 PRIVATE_SUPPORT 回傳同一組 content-free 狀態欄位；不可夾帶題目、摘要、作者或訊息。
- 帳號 analysis default 與逐篇 override 分開；訊息可用 `INHERIT`，實際匯出時須解析成 INCLUDED/EXCLUDED 並保留決策來源。

## 演進程序

1. 先提出 ADR 或契約變更說明，列出 producers、consumers 與資料 migration。
2. 更新 schemas、valid/invalid examples 與 contract tests。
3. 先部署能同時讀舊／新版本的 consumer，再更新 producer。
4. 經觀察期後才移除舊讀取路徑；fixtures 繼續保留回歸案例。
5. 不在未版本化的 `metadata` 中偷渡產品欄位；AuditEvent metadata 只允許列出的安全欄位。

## 時間與 secrets

- 所有 timestamp 使用 RFC 3339 date-time，必須包含 `Z` 或明確 UTC offset。
- Contracts 不提供 raw OAuth token、bot token、activation-code plaintext、私鑰或任意 secret 欄位；activation code 只保存 verifier hash。

## Task 18 activation-code v1 optional extension

Task 18 在`activation-code.schema.json`新增optional `binding`、`permissionProfile`與`redemptionRequestHash`。這些欄位不加入v1 required list，讓既有1.0 records仍有效；Task 18之後的新issuer則一律明寫三者。Binding只保存normalized value的SHA-256 fingerprint，不保存email或Discord user ID明文；idempotency也只保存request hash。

讀取legacy record時，consumer不得自行猜測權限。正式migration必須由operator補上經核准的permission profile，或拒絕redeem並要求重新核發；`binding`缺少時只代表legacy shape，不可自動解讀為已核准`NONE`。

## Task 26 raw thread export projection

`thread-export.schema.json` 與 `attachment-index.schema.json` 是新增的 1.0 document contracts，不改變既有 CaseMessage 或 ExportManifest。Thread export 把 message-level `INHERIT` 解析成實際 `INCLUDED`/`EXCLUDED`，並用 `analysisPermissionSource` 明寫是 account default 或 message override。這是 raw export，內部 user ID 與 Discord message ID 留給 Task 27 consent/anonymization pipeline 處理；consumer 不可把 Task 26 輸出當成可直接分析或公開的 sanitized package。

## 2026-07 Case ID decision

`caseNumber` 採 `Cxx-<6 random chars>-MMDD-HHMM[-P]`。`C99` 是非標準班級／特殊身份；token 使用獨立安全亂數，不得從姓名、學號、Email、Discord ID 或 internal UUID 推導。`case-id-mapping.schema.json` 是受保護 working-store contract，public projection 不得包含 `internalCaseId`。舊 `CALC-000421` fixture label 與 Private `null` 只屬 prototype v1 資料；本次 fixture baseline 直接更新為新格式，沒有 production data migration。
