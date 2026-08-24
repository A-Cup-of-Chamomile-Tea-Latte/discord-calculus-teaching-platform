# 案件生命週期決策（2026-08-22）

狀態：`ACCEPTED_FOR_PORTAL / RUNTIME_MIGRATION_COMPATIBLE`。

## 持久狀態

1. `OPEN`：新案件，尚未由教學團隊接手。
2. `TRACKED`：已有負責人，正在處理。
3. `IDLE`：自教學團隊最後回覆起 48 小時無學生回應，已寄出提醒。
4. `CLOSED`：由案件負責人手動結案。
5. `AUTO_CLOSED`：進入 Idle 後再 48 小時無學生回應，自動結案。

## 轉換規則

- `OPEN → TRACKED`：教學團隊接手。
- `TRACKED → IDLE`：第一段 48 小時無學生回應。
- `IDLE → TRACKED`：學生或自動寄信回覆帶來新活動。
- `TRACKED → CLOSED`：案件負責人手動結案；學生不得取得此控制。
- `IDLE → AUTO_CLOSED`：第二段 48 小時無學生回應。
- `CLOSED／AUTO_CLOSED → TRACKED`：有新回應時沿用原案件、案號與討論串。

「重新開啟中」是操作中的暫時文案；「已重新開啟」是時間軸事件。兩者都不是持久狀態。

## 標題規則

- 手動結案：加上 `✅` 前綴。
- 自動結案：加上既定 Bot 顏文字前綴。
- 重新開啟成功：移除結案前綴，標題週期加一，例如 `Title → Title 2`。

## 舊資料保留

舊值 `WAITING_FOR_STUDENT`、`ANSWERED`、`ESCALATED`、`TEMPORARILY_CLOSED`、`REOPENED` 不直接刪除。Portal 先透過相容轉換層讀取，避免破壞既有 fixture、GAS 與歷史契約；後續 migration 需另附 rollback 與資料對照收據。
