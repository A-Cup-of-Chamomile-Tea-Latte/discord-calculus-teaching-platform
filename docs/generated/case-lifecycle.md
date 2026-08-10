# 案件生命週期

> 由 `python -m tools.config_proposal generate` 自動產生。請修改 `config/proposed/`，不要直接編輯本檔。
> 以最新 Discord Side CONFIG 為展示依據。

## 狀態

- **Open** (`OPEN`)：新案件，尚未由教學團隊接手。
- **Tracked** (`TRACKED`)：教學團隊已接手；等待後續互動或結案。
- **Idle** (`IDLE`)：自教學團隊最後留言起 48 小時無學生回覆，已進入提醒。
- **Closed** (`CLOSED`)：由負責人手動結案。
- **Auto Closed** (`AUTO_CLOSED`)：Idle 後再 48 小時無回覆，自動結案。

## 允許轉移

- `OPEN` → `TRACKED`：`STAFF_CLAIM`（STAFF）
- `TRACKED` → `IDLE`：`FIRST_48H_WITHOUT_LEARNER_REPLY`（SYSTEM）
- `IDLE` → `TRACKED`：`LEARNER_REPLY`（LEARNER）
- `TRACKED` → `CLOSED`：`MANUAL_CLOSE`（STAFF）
- `IDLE` → `AUTO_CLOSED`：`SECOND_48H_WITHOUT_LEARNER_REPLY`（SYSTEM）
- `CLOSED` → `TRACKED`：`NEW_FOLLOW_UP_CYCLE`（LEARNER）
- `AUTO_CLOSED` → `TRACKED`：`NEW_FOLLOW_UP_CYCLE`（LEARNER）

## 計時

- TA 最後留言後 48 小時進入 Idle。
- Idle 後再 48 小時進入 Auto Closed。
- 不做語意式「輪到誰」判斷。
- Discord thread auto-archive 與產品案件狀態分離。
