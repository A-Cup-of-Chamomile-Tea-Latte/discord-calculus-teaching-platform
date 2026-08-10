# NAP BUILD 本機架構

## 目標與邊界

本輪把已確認的 Discord Side 設定轉為「可驗證設定 → 自動文件 → 本機視覺審查 → fixture provisioning plan」。所有路徑都停在 local/fixture 層；沒有 live adapter、credential loader、deployment 或 GO-APPLY。

```text
10_CFG_DiscordSide.zip（唯讀來源）
            |
            v
config/proposed/*.yaml -----> config/schema/*.schema.json
            |                           |
            +------ validator ----------+
            |
            +--> docs/generated/*.md
            +--> Config Studio（瀏覽器記憶體 draft）
            +--> Portal（fixture UX）
            +--> provisioning fixtures -> plan / diff / rollback / fake apply
```

## 元件

- `tools.config_proposal`：載入 JSON-compatible YAML、Draft 2020-12 schema validation、自訂引用／權限／Private Support／Bot scope 檢查及 deterministic 文件生成。
- `apps/config-studio`：Astro 靜態本機工具；提供 channel tree、roles、effective permissions、Forum、case lifecycle、Private Support、untrusted import、diff 與 export。
- `apps/portal`：既有 Astro Portal 的學生向改版；兩組 token theme、完整入口、fixture 表單、case lookup、狀態與情境庫。
- `tools.discord_provisioning`：嚴格 fixture parser、stable-key diff、rollback 與記憶體 fake apply。沒有網路或 live apply 介面。
- `tools/review/start-review.mjs`：啟動兩個 loopback-only Astro background server，Ctrl+C 逐一停止。
- `tools.reporting.render_rtf`：由 Markdown 來源產生 RTF 閱讀副本。
- `tools.packaging`：固定順序、timestamp、權限與壓縮設定的 deterministic safe handoff ZIP。

## 信任分區

- 可追蹤區：程式、schema、proposed config、fixtures、generated docs、測試與 screenshots。
- 私人證據區：歷年 dump／比較 ZIP，只讀取獲准的彙總報告，不進 Git 或交接 ZIP。
- 禁止區：真實學生資料、raw message、Private Support 內容、Discord／Google credentials、外部 LLM transfer。

## 已知遷移界線

Task 34 runtime contracts 仍保留 `ANSWERED`、`WAITING_FOR_STUDENT`、`TEMPORARILY_CLOSED`、`REOPENED` 等相容狀態；最新 proposed workflow 是 Open／Tracked／Idle／Closed／Auto Closed。Portal 以顯示層與新情境庫呈現最新規則，domain contract migration 留待另案，避免在未有真人審查下破壞既有資料契約。
