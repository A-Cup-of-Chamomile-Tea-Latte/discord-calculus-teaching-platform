# Local tools

由授權管理者明確執行的匯出、匿名化、批次匯入、Case ID 與 handoff 打包工具。工具不常駐監控、不自動傳送資料，也不納入真實資料 fixtures。

- `case_id/`：opaque random Case ID、解析／遮罩與 protected internal UUID mapping。
- `packaging/`：保留所有 fixtures、排除 operator data 的 deterministic handoff ZIP。
- `discord_provisioning/`：fixture-only declarative server plan parser、validator、diff、print 與 rollback plan；沒有 apply/network mode。
