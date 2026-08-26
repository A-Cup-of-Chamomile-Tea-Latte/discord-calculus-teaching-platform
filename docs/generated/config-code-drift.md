# 設定與程式差異

> 由 `python -m tools.config_proposal generate` 自動產生。請修改 `config/proposed/`，不要直接編輯本檔。
> 警告不會被誤報為完成；實際 domain migration 仍須後續審查。

| 等級 | 代碼 | 位置 | 說明 |
| --- | --- | --- | --- |
| — | — | — | 目前未偵測到差異 |

## 已知主要差異

- Live contracts、fixtures 與 Portal projection 已統一使用 Open／Tracked／Idle／Closed／Auto Closed。
- 舊狀態名稱只保留在 SQLite legacy read/migration adapter；`REOPENED` 是時間軸事件，不是持久化案件狀態。
- 115-1 已有 C01–C16 對應 M1–M4 的來源確認對照；Portal fixture 與實際 Discord membership 尚未套用。
- Canonical title 提案已更新為 `[M1 | C01][main tag] 標題`；正式 Discord runtime 仍使用舊格式，必須先接上可信任的 Class membership resolver。
