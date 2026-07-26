# TASK-06 report — 初始架構決策紀錄

## Outcome

完成。建立 12 份獨立編號 ADR、索引、Mermaid 系統脈絡圖與元件責任表；所有決策明確限定於 prototype scope，不表示正式部署或機構核准。

## Summary

將 monorepo、Astro static portal、GitHub Pages project site、GAS/Sheets 原型層、Python/discord.py、多 bot 分工、按需案件取得、本機匯出、一般案件查詢、Private Support 保護、不錄音／轉錄與 fixture-first 分別記錄。每份 ADR 均含正負／營運後果、替代方案、實際可行的 reversal strategy 與 open questions。

## Files changed

- `docs/decisions/README.md`：12 份 ADR 的編號、連結與原型狀態索引。
- `docs/decisions/ADR-0001-MONOREPO.md` 至 `ADR-0012-FIXTURE-FIRST.md`：各架構方向的獨立決策紀錄。
- `docs/architecture/CONTEXT.md`：Mermaid context diagram、信任邊界與 token／Private Support／匯出安全讀法。
- `docs/architecture/COMPONENTS.md`：13 個元件的責任、非責任、介面與 technical spikes。
- `docs/reports/TASK-06-REPORT.md`：本報告。

## Commands executed

- `sed`：重讀 defaults、shared context、Task 05 report、ADR template 與 Task 06 規格。
- `find`、`rg`：驗證 ADR 數量、必要章節、狀態、索引、Mermaid block、安全說明與 technical spike 標記。
- `npm run secrets`：掃描 Git 可提交候選檔。

## Verification

- Tests: ADR 結構 12/12 通過；架構文件檢查 2/2 通過。
- Linters/type checks: 本任務只新增 Markdown；secret scan 121 candidate files、0 findings。
- Builds: 不適用。
- Manual checks: 索引含 12 個連結；每份 ADR 都有 Consequences 與 Reversal strategy；diagram 沒有瀏覽器直接取得 bot token 的路徑；Discord/GAS 未驗證限制均標成 technical spike；沒有 production dependency 或部署動作。

## Diagnostics

- 最關鍵的信任邊界是：公開瀏覽器、受控 API/bots、外部平台、管理者本機資料區彼此分離。
- Private Support 以獨立 case type 與 deny-by-default policy 建模，而非只靠 UI 隱藏。
- 所有外部服務均維持 adapter/mock-first；contracts 與 fixtures 是後續 lane 的共同邊界。
- 實際 Discord intents/modal/forum/private mechanism、Apps Script quotas/locking/CORS 仍需後續 technical spikes。

## Assumptions made

- 共同背景已固定的方向標為 `Accepted（prototype scope only）`，不將其誤寫為 production-approved。
- ADR 編號依工作包順序建立；新證據需以 superseding ADR 保留歷史。
- 架構圖描述邏輯元件，不預設正式 host、網路 topology 或 cloud account。

## Risks and blockers

- 中度：Private Support 的正式 Discord mechanism 尚未驗證；目前 restricted backend/mock 足以安全推進 contracts。
- 中度：公開 case number 的枚舉風險需在 Task 12/29 確定 rate limit、欄位投影及是否加 PIN／登入。
- 低度：Mermaid 圖目前只做文字與結構檢查，未導入額外 renderer；不阻擋 Task 07。

## Questions for ChatGPT discussion

- 公開 case search 正式版是否需要 lookup PIN 或登入，還是最小欄位加 rate limit 足夠？
- Private Support 優先 technical spike 應比較 restricted backend、private thread 還是 restricted text channel？

## Recommended next action

執行 Task 07：依 ADR 的邊界建立版本化、語言中立 JSON Schemas、有效／無效範例及 contract validation tests。

## Copy-paste handoff

> TASK-06 已完成：建立 12 份獨立 ADR 與索引，涵蓋 monorepo、Astro static portal、Pages project site、GAS/Sheets 原型層、Python/discord.py、多 bot、按需查詢、本機明確匯出、一般案件公開編號、Private Support、無語音錄製及 fixture-first。12/12 ADR 都有 consequences 與 reversal strategy，且狀態明確限定為 prototype scope。另建 Mermaid context diagram 與 13 元件責任表；瀏覽器沒有 bot token 路徑，Private Support deny-by-default，Discord/GAS 未知均標 technical spike。架構檢查 2/2、secret scan 121 files 0 findings。下一步 TASK-07 JSON contracts 與 validation tests。
