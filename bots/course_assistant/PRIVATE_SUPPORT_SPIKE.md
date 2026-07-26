# Private Support Discord permission technical spike

Task 25 不宣稱 Discord private thread 或 restricted channel 已安全。Fixture 預設是 `BACKEND_ONLY`；以下檢查必須在獨立、無真實學生資料的 test guild 完成，並經隱私負責人核可後才能改變 representation policy。

## 候選方案

| 方案                   | 必須實測的問題                                                                                 | 本機預設           |
| ---------------------- | ---------------------------------------------------------------------------------------------- | ------------------ |
| Backend-only           | 後端身分驗證、教學團隊 ACL、保留與刪除、稽核存取                                               | 唯一啟用的 fixture |
| Discord private thread | 誰能發現／加入，parent channel permissions 是否洩漏，bot 離線或 thread archive 後的可見性      | 只有 enum/port     |
| Restricted channel     | Overwrite 繼承、role hierarchy、staff role 變動、channel 數量與刪除，以及 bot 失去權限後的狀態 | 只有 enum/port     |

## 必做測試

1. 以 owner、assigned TA、未指派 TA、普通學生、archive reader 與離開 guild 的帳號逐一測試 discover/read/send/history/attachment 結果。
2. 驗證 parent category/channel permission 變動、role 移除、thread archive/lock、case close、bot restart 與 bot role 降級後仍 fail closed。
3. 驗證 course assistant 只需最小 create/read/write/manage-own-representation 權限；禁止 `ADMINISTRATOR`、任意 role management 與 archive reader 可見性。
4. 驗證標題、notification、audit log、search、mention、attachment preview 與 mobile client 不會向非 participants 暴露存在性或內容。
5. 對 provider timeout 進行 reconciliation，確定不會重複建立或 fallback 到公開 channel。
6. 記錄每個 Discord client/version 的實測日期、screenshots、permission export 與清理證據；沒有通過前保持 `BACKEND_ONLY`。

## 上線前決策

- 最小 participant set 與 emergency escalation owner。
- Retention review 、closure、legal hold 與可恢復刪除政策。
- 是否完全排除 Discord，只在受控 backend 處理。
- Audit contract、稽核者權限與 incident response runbook。
