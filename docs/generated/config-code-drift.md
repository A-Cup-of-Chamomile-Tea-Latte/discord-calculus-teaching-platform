# 設定與程式差異

> 由 `python -m tools.config_proposal generate` 自動產生。請修改 `config/proposed/`，不要直接編輯本檔。
> 警告不會被誤報為完成；實際 domain migration 仍須後續審查。

| 等級 | 代碼 | 位置 | 說明 |
| --- | --- | --- | --- |
| WARNING | `LEGACY_STATUS_DRIFT` | `apps/portal|fixtures|contracts` | legacy Task 34 states remain for compatibility: ANSWERED (12 files), ESCALATED (9 files), REOPENED (8 files), TEMPORARILY_CLOSED (8 files), WAITING_FOR_STUDENT (11 files) |

## 已知主要差異

- Task 34 contracts 使用 `ANSWERED`、`TEMPORARILY_CLOSED`、`REOPENED` 等舊狀態；最新 Side CONFIG 使用 Open／Tracked／Idle／Closed／Auto Closed。
- 本輪 Portal 以顯示轉譯與新情境庫呈現最新提案；既有 fixture contracts 保留相容性並列為後續 domain migration。
- 115-1 已有 C01–C16 對應 M1–M4 的來源確認對照；Portal fixture 與實際 Discord membership 尚未套用。
- Canonical title 提案已更新為 `[M1 | C01][main tag] 標題`；正式 Discord runtime 仍使用舊格式，必須先接上可信任的 Class membership resolver。
