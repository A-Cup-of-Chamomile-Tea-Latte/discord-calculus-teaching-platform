# ADR-0002: Astro 靜態入口網站

- Status: Accepted（prototype scope only）
- Date: 2026-07-19
- Owners: Portal 維護者、教學團隊
- Related tasks: 09–14

## Context

入口網站需要可存取的繁體中文資訊架構、表單與單筆案件查詢，但第一版不需要常駐 application server。內容應可靜態發布，動態操作透過清楚的 adapter 邊界處理。

## Decision

使用 Astro + TypeScript、static output 與 plain CSS tokens。瀏覽器不持有 bot token、Google credentials 或服務端秘密；動態功能呼叫可替換的 API/mock adapter。

## Consequences

### Positive

靜態輸出部署面小、內容效能佳，並能先專注語意 HTML、可存取性與元件邊界。

### Negative

OAuth callback、受保護表單與私密資料不能只靠靜態頁面完成，仍需受控後端。

### Operational

所有 base path 與 API URL 必須可設定；Task 11/12 先用 fixture。正式 OAuth 與 CORS 行為須 technical spike。

## Alternatives considered

完整 SSR framework 能容納後端流程，但會過早引入 server 營運；純手寫 HTML 則不利於元件與型別共用。

## Reversal strategy

UI 元件與資料 adapter 分離；若需要 SSR，可改 Astro server adapter 或遷移至其他 framework，保留 contracts、CSS tokens 與靜態內容。

## Open questions

正式驗證流程應使用哪個受控後端，以及 Pages origin 與 Apps Script 的 CORS 限制仍待驗證。
