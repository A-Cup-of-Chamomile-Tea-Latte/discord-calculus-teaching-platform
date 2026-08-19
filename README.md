# Discord Calculus Teaching Support Platform

這是一個以繁體中文為主要學生介面的「微積分模組教學支援」原型。專案把 Astro 入口網站、Discord bots、Google Apps Script 管理層與本機匯出工具放在同一個 monorepo，以共用 JSON Schema 與完全虛構的 fixtures 進行驗證。

> 目前狀態：allowlisted Discord Guild 與兩隻 Mac runtime bots 已實機運作；本機 SQLite 是唯一案件權威來源。`Server Database` 已收斂為 5 個人用頁與 5 個隱藏機器頁，owner-only Apps Script Execution API 也已完成 Desktop OAuth 與一筆虛構案件的 preview／apply／冪等 smoke test。Portal 與 email 仍是 fixture／mock，Linux 24h host、live cutover 與正式試用尚未完成。以 [實作狀態](docs/IMPLEMENTATION_STATUS.md) 與 [下一步](docs/NEXT_STEPS.md) 為準。

## 先看平台責任

| 平台                     | 負責                                                                         | 不負責                                                                |
| ------------------------ | ---------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| **NTU COOL**             | 教材、作業、成績、期限、正式公告與課程政策                                   | 由本原型取代正式課務資訊                                              |
| **Discord**              | 問答、討論、助教回覆、資源整合與選用語音 office hour                         | 正式課務唯一來源；第一版不錄音、不自動轉錄                            |
| **Portal**               | onboarding、隱私指引、可選網站代送、一般案件查詢、Private Support 入口與狀態 | 持有 bot token；公開 Private Support；目前的 fixture 表單不會真正送出 |
| **Sheets / Apps Script** | 精簡行政投影、人工檢視與受控 Bridge                                           | 取代本機 SQLite、作高頻訊息資料庫或逐則 Discord mirror                |
| **本機 Python 工具**     | 由管理者明確啟動的匯出、同意判定、去識別化與批次匯入                         | 常駐監控、自動送往 AI 或未經審核的真實資料上傳                        |

網站代送是直接在 Discord 發問之外的替代路徑，不是學生必經流程。Private Support 是獨立的保護路徑，不得出現在公開案件查詢，且預設排除於教學分析匯出。

## 十分鐘 fixture demo

需要 Node.js 24.x、npm 11.x 與 Python 3.12–3.14。從 repository root 執行：

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
npm install
npm run check
npm run dev --workspace @calculus/portal
```

開啟終端顯示的 localhost URL，以案件編號 `C01-7K4M2Q-0702-1000` 體驗一般案件查詢。加入、一般提問與 Private Support 頁面只在瀏覽器中建立 fixture confirmation，不會儲存或發送。

完整網站與資料流示範見 [Fixture demo 指南](docs/FIXTURE_DEMO.md)；安裝、單項測試與 base-path 說明見 [本機開發指南](docs/architecture/DEVELOPMENT.md)。

## 常用命令

```sh
npm run check   # secrets、format check、lint、typecheck、全部測試
npm run build   # Portal static build + GAS local bundle
npm run dev --workspace @calculus/portal
```

範例資料流（不連網）：

```sh
python -m tools.discord_export C01-7K4M2Q-0702-1000 --adapter fixture --output-dir exports
python -m tools.anonymizer exports/C01-7K4M2Q-0702-1000 --output-dir local-data/sanitized
python -m tools.sheets_importer \
  exports/C01-7K4M2Q-0702-1000/metadata.json \
  local-data/sanitized/C01-7K4M2Q-0702-1000/sanitized-thread.json \
  --adapter dry-run
```

`exports/` 是未去識別化的本機 raw area；不可提交、公開或直接送往分析。`local-data/sanitized/` 仍須通過人工 checklist，不代表可逆或不可逆匿名性已獲保證。

## 專案導覽

- `apps/portal/`：Astro + TypeScript static portal。Astro 是目前實際的 framework 與 build system；未來的視覺 templates 只能作為可選起點，不是 runtime 或既定架構。
- `apps/gas/`：共用資料規則、附著式試算表管理選單，以及 owner-only Execution API Bridge。
- `bots/`：`course_assistant`、canonical `dump_bot`、相容用 `archive_reader` package 與共用 Python core；各 bot 維持權限分離，舊名不代表另一隻 bot。
- `tools/`：明確啟動的匯出、去識別化與 Sheets batch importer。
- `contracts/`：版本化 JSON Schema 與 valid/invalid examples。
- `fixtures/`：完全虛構、可重現的跨元件資料。
- `tests/`：契約、fixtures、Portal、GAS、bots 與 local tools 測試。
- `docs/`：架構、決策、安全、指南與任務報告；入口見[文件總覽](docs/README.md)，有效環境變數見[設定總覽](docs/CONFIGURATION.md)。

## 閱讀路徑

- 審查者：[架構概觀](docs/architecture/OVERVIEW.md) → [資料模型](docs/DATA_MODEL_OVERVIEW.md) → [部署邊界](docs/DEPLOYMENT_NOT_DONE.md)。
- 開發者：[本機開發](docs/architecture/DEVELOPMENT.md) → [Fixture demo](docs/FIXTURE_DEMO.md) → [ADR 索引](docs/decisions/README.md)。
- 學生：[學生快速指南](docs/guides/STUDENT_QUICK_GUIDE.md)。
- 助教：[助教快速指南](docs/guides/TA_QUICK_GUIDE.md) 與 [dump / follow / import 操作流程](docs/OPERATOR_WORKFLOW.md)。
- 提案審閱：[提案前言與執行摘要](docs/PROPOSAL_PREFACE_DRAFT.md)。

## 安全與發布邊界

本儲存庫的自動測試仍只使用虛構 fixtures。不得提交 secrets、真實學生資料、raw exports 或 deployment IDs；也不得因為測試通過，就自行 push、擴大 GAS access、寄信、公開網站、變更 Discord 權限或進行 live cutover。已核准的外部狀態與仍需人工授權的關卡，見 [部署邊界](docs/DEPLOYMENT_NOT_DONE.md)。
