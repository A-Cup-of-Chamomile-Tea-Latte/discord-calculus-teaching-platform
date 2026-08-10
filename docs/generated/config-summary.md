# 提案設定摘要

> 由 `python -m tools.config_proposal generate` 自動產生。請修改 `config/proposed/`，不要直接編輯本檔。
> 設定已驗證，但不是已套用 production 設定。

- 來源：`project-exchange/10_CFG_DiscordSide.zip` / `discord-side-config/CONFIG.md`
- 角色：10
- 分類：6
- 頻道／樣板：10
- Portal 頁面：12
- 案件狀態：5
- 驗證錯誤：0
- 驗證警告：1

## 安全邊界

- `fixtureOnly=true`；不連 Discord、Google、Email、OAuth 或 AI API。
- 沒有 `--apply`、token 欄位或部署入口。
- Class → Module 正式對照、資料保存政策與部分產品項目仍明確未決。
