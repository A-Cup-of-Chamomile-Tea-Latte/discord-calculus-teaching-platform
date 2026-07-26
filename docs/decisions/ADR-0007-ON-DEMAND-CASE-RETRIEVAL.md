# ADR-0007: 單筆按需案件取得

- Status: Accepted（prototype scope only）
- Date: 2026-07-19
- Owners: Portal、GAS 與 bot 維護者
- Related tasks: 12, 17, 23, 32

## Context

一般案件需要讓學生查詢進度，但持續輪詢所有案件會增加 Discord/GAS 配額、同步狀態與隱私風險。第一版的使用量與服務限制尚未驗證。

## Decision

以單一 case number 的 on-demand fetch、使用者明確 refresh 或 fixture lookup 為主；不建立全案件 continuous polling。

## Consequences

### Positive

外部呼叫與儲存量可預測，較容易限制資料揭露並以 mock 測試。

### Negative

狀態可能不是即時，使用者需要重新整理；每次按需查詢仍要有 rate limiting 與不存在案件的安全回應。

### Operational

CaseLookup adapter 只回傳公開允許欄位。GAS cache、Discord fetch 限制與合理 refresh interval 需 technical spike。

## Alternatives considered

WebSocket／event-driven 同步或定時全量 polling 可提供較新狀態，但第一版增加後端與一致性成本，且沒有需求證據。

## Reversal strategy

在 contract 中保留 `updatedAt`、source 與 cache metadata；若未來需要 push/event sync，可新增 indexer，不改 Portal 的 CaseLookupResponse 介面。

## Open questions

快取時間、查詢 rate limit、狀態延遲提示與 Discord/GAS quota 需在實測後決定。
