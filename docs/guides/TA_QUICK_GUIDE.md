# 助教快速指南

> 這是試用前操作指南，不是授課單位核准的正式 SOP。Discord 測試 Guild、兩隻 Mac bots 與精簡 Sheet／GAS Bridge 已完成實機或虛構案件驗證；Portal、email、Linux host、live cutover 與正式學生試用仍未放行。

## 一般案件 triage

1. 確認這是一般課程討論，不含需 Private Support 的敏感內容。
2. 確認案件狀態，只使用 `OPEN`、`WAITING_FOR_STUDENT`、`ANSWERED`、`ESCALATED`、`CLOSED`。
3. 回覆時確認作者顯示、可見範圍與 analysis permission；三者不可相互推導。
4. 需學生補件時設 `WAITING_FOR_STUDENT`；需教師/負責助教判斷時設 `ESCALATED` 並留下非敏感責任紀錄。
5. 正式課務問題一律指回 NTU COOL 上的公告或政策，不在 Discord/Portal 自行建立矛盾版本。

## Private Support

- 只允許 owner 與 explicit teaching-team participants，不用公開 case number。
- 只能在受保護 representation 或 backend 處理；原型預設是 backend-only fixture，未驗證正式 Discord private mechanism。
- 分析與內容匯出預設 deny；不得為了 demo 或調試而解除。
- 升級時只新增必要參與者，並觸發必要的 metadata-only audit。
- 關閉後仍要依保留 review hook 檢視；原型的 30 日是 review trigger，不是已核准的保留期限。

## 匿名回覆

匿名學生不可用普通 Discord reply，否則會顯示帳號/暱稱。應使用 Portal 或 Discord modal，由 `course_assistant` 在授權後代貼。不可採「先發、立即刪」；刪除不能抹除 notifications、logs 或已看到的內容。

## Dump / follow / import

- 只由授權管理者對明確選定的 general-case thread 執行。
- raw export 是敏感 local data，不得 commit、公開或直接送往 AI。
- 必須依序通過 consent/anonymizer 與 human review checklist。
- 舊的 CLI Sheets importer 只作 dry-run／CSV／mock，不得繞過 SQLite 與可靠 outbox 直接寫正式 Sheet。現行投影由受控 Bridge 執行。
- 具體指令、checkpoint、idempotency 與失敗處理見 [操作員流程](../OPERATOR_WORKFLOW.md)。

## 系統不可用或疑似事故

1. 停止表單、export/import 或 live test；不把敏感內容複製到公開 issue/chat。
2. 正式課務回 NTU COOL；一般提問使用已公告備援管道；Private Support 使用受保護連絡方式。
3. 只記錄事件類別、時間、受影響元件與處理狀態，不複製 token、驗證碼或學生原文。
4. 通知授權 owner 停用/revoke 受影響 token、deployment 或 artifact；原型不自動執行外部撤銷。
5. 在重新開啟前完成最小權限、暴露範圍、日誌與資料保留複核。
