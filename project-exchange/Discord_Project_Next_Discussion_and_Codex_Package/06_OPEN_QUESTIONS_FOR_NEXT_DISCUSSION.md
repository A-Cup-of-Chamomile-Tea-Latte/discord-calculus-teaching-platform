# 下一輪待討論問題

以下問題不應由 Codex 自行決定。可在 Codex 執行安全基礎工作時，由 ChatGPT 與專案負責人逐項討論。

## A. 身份與角色

1. Professor、TA、Student、Admin、Approved Guest 各需要哪些 Discord roles？
2. 班級要用 role、Forum tag，還是 database 欄位？
3. `nnmmm` 是否永遠作為預設 nickname？
4. 真名、alias、anonymous 三種模式如何切換？
5. 特許成員可看到哪些區？
6. 所有 TA 是否看得到所有班？

## B. 頻道與 Forum

1. 一個全課程 Forum，還是每班一個 Forum？
2. Class questions 是否需要獨立區？
3. Resource sharing 是否與 questions 分開？
4. General chat 是否開放所有人？
5. Voice office hour 是否一開始就建立？
6. Forum tags 最小集合是什麼？

## C. Private Support

1. 使用 private thread、restricted channel，還是 backend-only？
2. 誰預設可見？
3. 學生如何在 Discord 一鍵建立？
4. 學生如何在網站建立？
5. Private Support 是否有私人案號？
6. Private Support 是否允許 attachment proxy？
7. 誰可以手動結案？

## D. 案件查詢與補充

1. 查詢只靠完整案號，還是需要 Email／session？
2. 補充內容是否需要驗證原提問者？
3. 是否允許訪客補充？
4. 何謂已讀？
5. 未登入頁面開啟能否算已讀？
6. Timeline 要顯示到什麼細度？
7. `Last Response` 是否只計 TA／Teacher？

## E. AI 同意

1. Original poster 選 No 是否整案完全排除？
2. Original poster 選 Yes 時，其他學生回覆如何處理？
3. TA／教師回覆是否統一允許？
4. 帳號預設與逐案選項的優先順序？
5. 撤回同意後，既有 sanitized export 如何處理？
6. 正式研究與內部教學改善是否使用不同同意文字？

## F. 同步與主機

1. Bot 是否只在課程時段開啟？
2. 需要多少資料即時性？
3. Last Synced 可以容忍多久？
4. 本機、朋友主機、校內主機或 VPS，哪個適合？
5. Bot 離線時網站如何降級？
6. Reconciliation 頻率？
7. 每週維護由人工還是 trigger 啟動？

## G. Google Sheets／GAS

1. Working spreadsheet 每學期分開嗎？
2. Closed cases 移到另一個 spreadsheet 嗎？
3. 完整文字是否放 GSheet？
4. 是否改用 Drive JSON／Markdown？
5. GAS 只負責 API 與 trigger，還是也寄 verification Email？
6. 何時才需要 Workspace？
7. 是否需要 SQLite／PostgreSQL？

## H. 舊 Server 研究

1. 112／113／114 server 是否允許 `dump_bot` 加入？
2. 先只抓結構，還是同時抓 thread counts？
3. 是否允許讀取 message metadata？
4. 何時才讀 message bodies？
5. 誰負責對 TA／Student role 做人工映射？
6. 去識別化後可否作 fixtures？
7. 是否比較各年回覆時間與活躍度？

## I. 測試

1. 哪些朋友帳號協助測試？
2. 是否需要兩個普通 Discord 測試帳號？
3. 測試帳號可以使用假姓名嗎？
4. 測試 server 是否完全獨立於正式 server？
5. 哪些流程必須真人操作？
6. 何時開始教授／TA usability review？

## 下一輪建議優先順序

1. 最小身份架構。
2. `course_assistant` 與 `dump_bot` 權限。
3. Test server 最小 channel tree。
4. Private Support 承載方式。
5. 案件查詢與補充驗證。
6. Bot 開啟時段與 GSheet working model。
7. 舊 server structure-only inventory。
