# ADR-0012: fixture-first 開發

- Status: Accepted（prototype scope only）
- Date: 2026-07-19
- Owners: 全體維護者
- Related tasks: 07–33

## Context

正式 Discord、Sheets、email、OAuth 與學生資料尚未授權，也不應為本機開發與 CI 的必要條件。各 lane 仍需共同驗證資料與流程。

## Decision

先建立版本化 JSON contracts、完全虛構 fixtures 與 mock adapters。所有 Portal、GAS、bot 與 tool 的基礎測試在無網路、無 secret、無正式帳號時可執行；外部 integration 另行授權。

## Consequences

### Positive

CI 可重現、沒有真實資料風險，各元件能並行實作並用相同案例驗證。

### Negative

Mocks 可能與真實 API 行為不一致；通過 fixture test 不代表配額、權限或網路整合可用。

### Operational

Fixtures 必須穩定、可讀且通過真實資料／secret pattern guard。所有 mock 結果明確標示，不宣稱 production readiness。

## Alternatives considered

直接連 sandbox／正式服務可較早發現限制，但需要 secrets、外部寫入與治理授權，不適合 foundation。

## Reversal strategy

Adapter interface 不變，逐一加入可選的 real-service implementation 與 gated integration tests；fixtures 繼續作 regression baseline，不因接入外部服務而刪除。

## Open questions

Discord、GAS、email 與 OAuth 的 sandbox 策略、測試帳號及批准流程需各 lane technical spike 後決定。
