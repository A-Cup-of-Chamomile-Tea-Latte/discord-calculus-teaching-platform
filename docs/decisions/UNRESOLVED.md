# 未決事項

本清單只記錄會影響產品或架構、且尚未由 `CODEX_TASKS/01_SHARED_CONTEXT.md` 固定的事項。

| ID    | 未決事項                                                                                               | 目前保守預設                                                                                            | 最晚決策點                     |
| ----- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------- | ------------------------------ |
| U-002 | Astro、discord.py 等套件對 Python 3.14 / Node 24 的實際相容性                                          | 使用專案本機相依套件；必要時以 Python 3.12/3.13 驗證                                                    | Task 04、11、21                |
| U-003 | GitHub project-site 的 repository 名稱與最終 base path                                                 | 暫用 `discord-calculus-teaching-platform` 作為可覆寫預設，不部署                                        | Task 14 部署授權前             |
| U-004 | Discord 與 Apps Script 的實際配額、權限與限制                                                          | 僅建 mock/interface，將未知部分標為 technical spike                                                     | Tasks 15–25                    |
| U-006 | 教學分析同意的正式政策文字、其他作者訊息規則與撤回流程                                                 | 強制逐案 Yes/No；OP No 整案排除，OP Yes 仍保留其他作者訊息層級過濾；不宣稱校方核准                      | 正式資料或 AI 分析前           |
| U-007 | Portal/GAS如何把已授權write command送到course_assistant                                                | 禁止browser直連；暫以authenticated backend/queue port建模，不選定host                                   | Task 32                        |
| U-008 | course_assistant是否需要privileged Guild Members intent                                                | baseline關閉；優先targeted REST/member from interaction，只有證明需要lifecycle/list events才申請        | Tasks 21、22、30               |
| U-009 | Private Support使用private thread、restricted channel或backend-only representation                     | 全部deny-by-default，Task 25只做fixture比較，不先給reader存取                                           | Tasks 25、29、32               |
| U-010 | Anonymous reply 的 private audit 應擴充現有 audit-event contract 或另建 message-operation contract     | Task 24 先用 metadata-only typed private sink，不擴充現有 enum，不記 raw body                           | Tasks 29、32                   |
| U-012 | Portal 正式後端與 browser authenticated transport；不得直接借用 GAS owner authority                      | 現行 Bridge 只用 owner-only Execution API；不提供公開 Web App，也不把 Desktop OAuth 放進瀏覽器          | 正式 Portal 試用前             |
| U-013 | Raw/sanitized export、email/contact、consent/audit 與 Private Support 的保留、撤回、刪除與 backup 政策 | 不使用真實資料；本機測試產物不外傳，Private Support 只作 backend-only fixture                           | Tasks 31–33                    |
| U-014 | Consent 在匯出／分析時的 versioned snapshot、撤回後重處理與 AI release approval                        | 只有 raw policy 與 current consent 都 INCLUDED 才生 sanitized content；人工複核前不送往 AI              | Tasks 31–33                    |

## 已固定、不在本清單重開的決策

- NTU COOL 是課務正式依據，Discord 與入口網站只作補充。
- 不錄音、不自動語音轉錄。
- Private Support 與一般公開案件分流；逐案 AI 選擇會保存，但不自動匯出或送往 AI。
- 第一版不持續輪詢所有案件，不自動進行 LLM 分析。
- 開發只使用 fixtures，不使用真實學生資料或 secrets。

## 2026-07-23 交接已解決的事項

依 `project-exchange/Discord_Project_Next_Discussion_and_Codex_Package/01_PRODUCT_DECISIONS_UPDATE.md`：

- 原 U-001：案件顯示格式改為 `C12-7K4M2Q-0907-2007`；特殊班級使用 `C99`，Private Support 加 `-P`，隨機 token 不由個資衍生。內部可另用 UUID。
- 原 U-011：GitHub Pages 只作靜態入口；production 不預先建置真實案件頁。真實案件使用 one-case-at-a-time lookup，實際驗證 backend／hosting 仍由 U-007、U-012 管理。
- `Last Update` 是任何案件變化；`Last Response` 是最後一次教學團隊文字回覆。附件只顯示 marker 與 Discord deep link，第一版不下載、代理或重新託管附件。
- Discord Gateway changed-case queue、1–5 分鐘批次 projection、15–60 分鐘 active-case reconciliation 與每週 archive 是目標模型；不得把它解讀成全 server continuous polling。

## Task 33 後 access-scope review

GitHub Pages 是 internet-public，但產品語意的 course-wide public 是相對於私訊的課程成員可見，不等於全網公開。現在的預建案件頁與 fixture case list 只含虛構資料，本輪不修改 Portal、GAS routes、fixtures 或案件頁。Tasks 26–33 完成後應一併決定：

- course-session access gate；
- production 是否保留 list-all-cases route；
- 是否只允許 one-case-at-a-time lookup；
- 未登入時可見欄位。

## 2026-08-10 已解決或收斂的事項

- 原 U-015：ZIP、三年度 dump、live runtime state 與 local archive 已排除 Git；可追溯 source
  checkpoint 只包含已掃描的程式、fixtures、文件與小型審查圖片。當時尚未建立 remote；現況改由
  `docs/IMPLEMENTATION_STATUS.md` 記錄。
- 2026-08-10 當時由 Local SQLite 擔任 operational authority；完成 cutover 後已改為 Remote SQLite。
  Sheets 始終只是行政 projection；任何 restore 都必須通過完整性與人工確認，不能自動覆蓋 authority。
- Email `SENT` 表示 sender call 與 audit write 成功，不表示送達或已讀。
- AI analysis 仍須明確同意、去識別化與教學優化限定用途；U-006、U-013、U-014 保留，以便
  完成正式文字、撤回、retention 與逐作者規則。

## 2026-08-24 已解決或收旂的事項

- 原 U-005 的顯示欄位已由 ADR-0013 固定：General 與 Private 共用 one-case-at-a-time 查詢，只顯示案號、類型、五態、更新時間、是否回覆與 Discord 連結。身分驗證、rate limit 與保留期限仍由 U-012／U-013 追蹤。

## 2026-08-19 已解決或收斂的事項

- Standalone GAS 已固定為 `executionApi.access=MYSELF`，本機 Bridge 以 Desktop OAuth 呼叫 `scripts.run`；歷史 Web App manifest 與公開 HTTP 入口不再是現行部署面。
- `Server Database` 已收斂為 5 個人用頁與 5 個隱藏機器頁。舊 21 個空受管頁籤已由 migration 安全移除。
- SQLite 是唯一案件 authority；Google failure 只讓 Bridge degraded，Discord writer 不會因此改以 Sheet 為準。
- U-012 仍保留，因為 Portal 若要接真實案件，仍須另選 authenticated backend 與 browser access policy；owner-only Execution API 不等於學生端 API。
