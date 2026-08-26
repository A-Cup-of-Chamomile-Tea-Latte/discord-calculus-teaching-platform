# 助教快速指南

> 這是試用前操作指南，不是授課單位核准的正式 SOP。Remote Linux 已是唯一 writer，production v6
> observation 已於 2026-08-24 PASS；candidate v10 仍須通過 deployment smoke、白帳號 E2E 與 rollback
> readiness。Portal join／lookup 與 email verification 已在候選版完成，但正式 GAS sender、
> production session 與學生試用尚未放行。

## 一般案件 triage

1. 確認這是一般課程討論，不含需 Private Support 的敏感內容。
2. 確認案件狀態，只使用 `OPEN`、`TRACKED`、`IDLE`、`CLOSED`、`AUTO_CLOSED`。
3. 回覆時確認作者顯示、可見範圍與 analysis permission；三者不可相互推導。
4. 接手後設為 `TRACKED`。教學團隊最後回覆後 48 小時無學生回應才進入 `IDLE`；再 48 小時才自動結案。只有案件負責人可手動結案。
5. 結案後有新回應時沿用原案號與討論串回到 `TRACKED`；「已重新開啟」只記在時間軸。
6. 正式課務問題一律指回 NTU COOL 上的公告或政策，不在 Discord/Portal 自行建立矛盾版本。

## Private Support

- 頻道只允許 requester、Bot、TA、教師與明示授權的 system admin；正式使用前以白帳號驗證 ACL。
- 教學團隊真正回覆後 48 小時無學生回應才進入 `IDLE`；再 48 小時無回應才自動結案。
- 自動結案會先凍結 requester 發言、執行 `private down` 對應的 dump job 並驗證 manifest；只有
  `VERIFIED` 才能刪除 Discord 頻道與清除 operational DB 內的正文、連結及 requester ID。
- 匯出或刪除失敗時保留頻道，使用 `/ops attention-*` 接管；已安全刪除後再求助則以
  `/ops replacement-case` 建立新 Private case。

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

## 需要人工處理的工作

- `/ops status` 只用來看 queue 深度與 safe error code，不代表問題已解決。
- 不直接用 `sqlite3 UPDATE` 隱藏失敗紀錄，也不盲目重跑可能已完成的 Discord／email side effect。
- v10 候選版提供 system admin 專用的 `/ops attention-list`、`attention-inspect`、
  `attention-retry`、`attention-resolve` 與 `/ops replacement-case`；只操作 allowlisted queue
  欄位並留下 audit，不接受任意 SQL。
