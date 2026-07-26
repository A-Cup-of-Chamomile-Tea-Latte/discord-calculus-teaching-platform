# TASK-05 report — 專案章程、提案前言與詞彙表

## Outcome

完成。新增三份繁體中文、面向教授與助教可讀的產品文件；沒有新增產品功能或改變固定決策。

## Summary

將共同背景整理成專案章程、提案前言草案與一致詞彙表。文件清楚說明教育問題、目標／非目標、利害關係人、第一版範圍、成功訊號、平台邊界及尚未定案項目；避免宣稱機構核准或誇大自動化與 AI 效益。

## Files changed

- `docs/PROJECT_CHARTER.md`：英文專案名稱、教育問題、目標、非目標、利害關係人、V1 範圍、平台責任、成功訊號、原則與未決事項。
- `docs/GLOSSARY.md`：統一 NTU COOL、portal、case、Discord 結構、Private Support、身份、fixture/mock/adapter、dump/follow 與 analysis permission 等用語。
- `docs/PROPOSAL_PREFACE_DRAFT.md`：以教育摩擦與助教重複工作為主的提案前言草案。
- `docs/reports/TASK-05-REPORT.md`：本報告。

## Commands executed

- `sed`：重新讀取 defaults、shared context、Task 04 report 與 Task 05 規格。
- `rg`：檢查簡體字形、固定狀態詞彙、必要詞彙與未決標示。
- `npm run secrets`：確認新增文件沒有明顯 secret pattern。

## Verification

- Tests: 文件檢查 4/4 通過——三份必要文件存在、必要詞彙齊全、平台邊界一致、未決事項有標示。
- Linters/type checks: 本任務只新增 Markdown；未改動程式碼。secret scan 通過。
- Builds: 不適用。
- Manual checks: 明確包含 goals、non-goals、stakeholders、first-version scope、success signals；明確說明 Discord 不取代 NTU COOL、網站代送是替代方案、AI 分析延後且由明確匯出啟動、未宣稱機構核准。

## Diagnostics

- 文件中將作者顯示、可見範圍與 analysis permission 分成三個概念，避免後續 UI／contract 混用。
- 對 `forum post`、`thread`、`text channel` 分別定義；實際 Discord 映射仍標為待 technical spike。
- 成功訊號目前採可觀察行為，不捏造量化改善幅度。

## Assumptions made

- 英文專案名稱採根 README 的 `Discord Calculus Teaching Support Platform`，正式提案名稱仍可調整。
- `nnmmm` 的中文統稱暫用「課程代號」，並保留英文 `course alias` 以對應契約。
- 「教學分析同意」是工作用語；正式告知與撤回文案仍未定案。

## Risks and blockers

- 中度：正式資料保留、撤回、研究／教學分析的治理文字尚未決定；Task 27、29、31 必須持續標為草案，不能默認核准。
- 低度：Discord private mechanism 的實際選擇未驗證；不阻擋 fixture-first contracts。
- 無阻擋 Task 06 的問題。

## Questions for ChatGPT discussion

- 教學分析未來是否只作課程改善，或可能成為研究資料？兩者需要不同的告知與審查流程。
- 成功訊號在試用前應由誰轉成可量化且不造成監控壓力的評估指標？

## Recommended next action

執行 Task 06：把已固定架構方向寫成可逆 ADR，並建立 context diagram 與 component responsibility table。

## Copy-paste handoff

> TASK-05 已完成：新增繁體中文 `PROJECT_CHARTER.md`、`GLOSSARY.md`、`PROPOSAL_PREFACE_DRAFT.md`。章程包含教育問題、目標／非目標、利害關係人、第一版範圍、平台責任、成功訊號與未決事項；前言清楚說明 Discord 只補充 NTU COOL、網站代送為可選路徑、AI 分析須在明確匯出與同意處理後由人員延後啟動，不是監控；詞彙表區分作者顯示、可見範圍、analysis permission，以及 forum post/thread/text channel。文件不宣稱機構核准或技術成效。必要文件與內容檢查通過，無程式碼／build 變更。主要未決為資料治理文案及正式 Discord 機制，下一步執行 TASK-06 ADR 與架構圖。
