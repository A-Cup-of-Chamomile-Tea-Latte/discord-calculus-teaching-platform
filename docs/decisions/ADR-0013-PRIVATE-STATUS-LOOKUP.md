# ADR-0013: Private Support 最小狀態查詢與逐案 AI 選擇

- Status: Accepted（repository candidate；尚未部署）
- Date: 2026-08-24
- Supersedes in part: [ADR-0010](ADR-0010-PRIVATE-SUPPORT-PROTECTION.md)

## Context

新版 Portal 將案件查詢定位為過渡性、一次一案的狀態服務；完整內容仍回 Discord 查看。舊 ADR-0010 將 Private Support 完全排除於查詢，並將分析選擇強制為 `EXCLUDED`，已不符合 2026-08-24 產品審查。

## Decision

1. 一般與 Private Support 使用同一個案號查詢介面；只接受完整案號，不提供 list-all、搜尋建議或背景 polling。
2. 查詢只回傳案號、類型、五態、更新時間、是否已有教學團隊回覆與 Discord 直達連結；不回傳題目、訊息、作者、附件或內部 ID。
3. Private Support 仍使用獨立受限 Discord 空間、`C99…-P` 案號與 `PRIVATE` 可見度；可查狀態不等於可讀內容。
4. `/private open` 與公開案件共用 main tag 與逐案 AI 選擇。選擇可被保存，但 Private 內容仍不自動匯出或送往 AI；匯出需另外的治理與人工 release gate。

## Compatibility

- 新建 `case-status-lookup-response.schema.json` 作為當前最小投影。
- 舊 `case-lookup-response.schema.json`、GAS case API 與 fixtures 保留為 legacy prototype compatibility，不得當作新 backend 的產品契約。
- 未完成 same-origin backend、rate limit 與 audit 前，Portal public build 繼續 fail closed。
