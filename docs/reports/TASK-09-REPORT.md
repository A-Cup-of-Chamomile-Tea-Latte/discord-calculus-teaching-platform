# TASK-09 report — Portal 資訊架構與使用者流程

## Outcome

完成。建立 route map、導覽階層、公開／私密邊界、六種學生 journey、教學團隊 triage、八種 failure/fallback、八個必要頁面 wireframe 與內容清單；未選模板或實作框架。

## Summary

Portal IA 將首頁 case-number search 放在第一主內容區塊，並把直接 Discord、網站代送（替代方案）及 Private Support 三條路徑清楚分開。Public case detail 只允許 GENERAL projection；Private Support 沒有通往 public search 的資料流。所有相關頁面標示 NTU COOL 的正式課務權威。

## Files changed

- `apps/portal/docs/INFORMATION_ARCHITECTURE.md`：route map、navigation、page ownership/runtime、trust boundary、external return points。
- `apps/portal/docs/USER_JOURNEYS.md`：學生／教學團隊流程與 failure/fallback table。
- `apps/portal/docs/WIREFRAMES_AND_CONTENT.md`：八個必要頁面文字 wireframes、component states 與 content inventory。
- `docs/reports/TASK-09-REPORT.md`：本報告。

## Commands executed

- `sed`：重讀 defaults、shared context、Task 08 report 與 Task 09 規格。
- `rg`：驗證必要 routes、頁面 ownership、替代方案、Private Support、NTU COOL、static/adapter 與 fallback 關鍵字。
- `npm run secrets`：確認文件沒有明顯 secret pattern。

## Verification

- Tests: 文件需求檢查 10/10 通過（8 routes + boundaries/journeys inventory）。
- Linters/type checks: 本任務只新增 Markdown；secret scan 通過。
- Builds: 不適用，Task 09 明確先設計、尚未建立 Astro。
- Manual checks: 首頁 prominent search 位於首個主區塊；網站代送每處標「替代方案」；Private Support 沒有 public case flow；NTU COOL authority 在首頁/detail/ask/guide/footer；教授可由三張 Mermaid 圖理解主流程。

## Diagnostics

- 靜態 Pages 能呈現內容與互動 shell，但 OAuth、email、submission、Private Support 與正式 case lookup 都需要受控 backend adapter。
- Public detail 不應重用完整 Case record，應使用 CaseLookupResponse／公開 conversation projection。
- 無 JavaScript fallback 仍可提供平台邊界與外部連結，但不能假裝查詢／表單已執行。

## Assumptions made

- Routes 採 `/cases/` 與 `/cases/[caseNumber]/`；Task 11 可用 fixtures 預產 detail，Task 12 另提供 on-demand client adapter。
- 正式 NTU COOL/Discord URL 尚未確認；IA 指定位置，實作先用清楚的 disabled/mock link，不捏造 production target。
- Portal 第一版不做完整 teaching-team dashboard；triage 流程由 GAS/Discord lane 承擔管理介面。

## Risks and blockers

- 中度：GitHub Pages static hosting 無法自行安全處理私密提交與 OAuth callback；Task 11–14 只能保留 adapter boundary。
- 中度：Public conversation projection 尚未獨立 schema；Task 12 應只映射允許公開欄位，不暴露 internal/Discord IDs。
- 無阻擋 Task 10 的問題。

## Questions for ChatGPT discussion

- 正式 Portal 是否需要 teaching-team dashboard，或管理功能只留在 Discord/GAS？目前不影響學生 prototype。
- Public case detail 最終是否顯示完整允許公開的 conversation，或只顯示 teaching-team latest response？Task 12 可先用 fixture 完整公開 thread。

## Recommended next action

執行 Task 10：以 plain CSS tokens 與可存取元件建立 mobile-first、刻意低擬真的 visual foundation 和 fixture component gallery。

## Copy-paste handoff

> TASK-09 已完成：定義 `/`、`/cases/`、`/cases/[caseNumber]/`、`/join/`、`/ask/`、`/private-support/`、`/guide/`、`/status/` 的 route map、navigation、page ownership、static/adapter 界線、六種學生 journeys、教學團隊 triage、八種 failure/fallback 與文字 wireframes/content inventory。首頁案件查詢位於第一主區塊；網站代送明標「替代方案」；Private Support 沒有 public-search 資料流；NTU COOL authority 出現在相關頁面。文件需求 10/10 通過，未選模板、未連 backend。下一步 TASK-10 plain CSS design tokens + accessible components/gallery。
