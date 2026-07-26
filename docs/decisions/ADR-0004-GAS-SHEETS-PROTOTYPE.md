# ADR-0004: Apps Script / Sheets 只作原型與行政層

- Status: Accepted（prototype scope only）
- Date: 2026-07-19
- Owners: GAS 維護者、課程管理者
- Related tasks: 15–19, 28, 32

## Context

課程管理者熟悉 Google 工具，Sheets 適合檢視少量使用者、案件索引、同意、啟用碼與 audit records；但 Apps Script/Sheets 有配額、併發與資料一致性限制，不適合高頻逐訊息寫入。

## Decision

Apps Script / Sheets 僅作 prototype/admin layer。原始 Discord 訊息由本機明確匯出後批次匯入，不同步寫入每一則事件。`clasp` 只管理原始碼，不作資料上傳工具。

## Consequences

### Positive

行政人員可在熟悉介面檢視小量資料，原型成本低。

### Negative

效能、交易語意、權限模型與配額不等同正式資料庫，不能假設能承擔尖峰負載。

### Operational

所有資料操作經 adapter；本地只建 source/mock，不建立雲端專案。配額、LockService、CORS 與 Web App 權限需 technical spike。

## Alternatives considered

正式 SQL/managed backend 較穩健，但原型期增加部署與維運；直接同步 Discord 每則訊息會擴大隱私與配額風險。

## Reversal strategy

保持 JSON contracts 與 storage adapter；若負載或治理需求超過 Sheets，新增資料庫 adapter、遷移批次資料，Portal/bots 不直接依賴 sheet 欄位。

## Open questions

正式配額、資料保留、管理者權限與備份策略尚待 technical spike 與治理決策。
