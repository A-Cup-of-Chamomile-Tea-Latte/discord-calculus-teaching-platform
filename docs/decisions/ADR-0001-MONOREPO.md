# ADR-0001: 使用 monorepo

- Status: Accepted（prototype scope only）
- Date: 2026-07-19
- Owners: 教學團隊、系統維護者
- Related tasks: 03, 07, 08, 30, 32

## Context

Portal、Apps Script、Discord bots 與本機工具必須交換一致的案件、訊息、同意及匯出資料。若各自成為獨立 repository，原型期很容易產生 schema 與 fixtures 漂移。

## Decision

以單一 repository 管理 `apps/`、`bots/`、`tools/`、`contracts/`、`fixtures/`、`tests/` 與 `docs/`，用目錄責任與 contract tests 控制邊界。

## Consequences

### Positive

共用契約、fixture 與跨元件變更能在同一個 review 中驗證。

### Negative

不同語言工具鏈共存，CI 與相依套件管理較複雜；未設界線時可能出現跨目錄耦合。

### Operational

各 lane 只修改自己的主要路徑；共用 contract 變更須是明確、可追蹤的原子變更。

## Alternatives considered

每個元件各自一個 repository 能獨立發布，但原型尚小，版本協調成本高於隔離收益。

## Reversal strategy

contracts 與 adapters 保持語言中立；未來可依 `apps/`、`bots/`、`tools/` 歷史拆庫，將 schemas 發布為版本化 artifact。拆分前先建立跨庫 contract CI。

## Open questions

何時元件發布週期或權限差異大到值得拆庫，留到正式營運設計決定。
