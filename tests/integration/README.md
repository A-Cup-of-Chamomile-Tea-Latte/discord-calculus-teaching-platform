# Integration tests

以 fixtures 與 mock adapters 驗證跨元件流程，不連正式 Discord、Sheets、email 或 OAuth 服務。

`test_fixture_journey.py` 是 Task 32 的單一可重複端對端旅程：

1. 讀取並驗證 Portal general-question fixture；
2. Course Assistant 透過 writer port 建立本機 thread representation/mapping；
3. Portal lookup fixture 只找到 general case，Private Support 沒有 public number；
4. anonymous follow-up 經 modal definition + Course Assistant service/writer path；
5. `dump_bot` 只在 explicit dump 後做 bounded fixture reads；
6. Task 26 exporter 寫 JSON/Markdown/metadata/attachments；
7. Task 27 anonymizer 產生 consent-filtered package；
8. Task 28 importer 以 dry-run adapter 列出 curated rows。

測試沒有 scheduler/sleep、network client、credential 或 cloud resource。Production gates 與回滾點見 `docs/architecture/PRODUCTION_INTEGRATION_PLAN.md`。
