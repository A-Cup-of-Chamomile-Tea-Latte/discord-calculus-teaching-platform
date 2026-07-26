# Codex 指令包使用說明

這個壓縮包不是成品程式，而是一組可以交給 Codex 逐批執行的 `.md` 交接文件。

## 建議放置位置

將本資料夾內容放到：

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

本地資料夾使用中文與空格沒有問題；執行 shell 指令時要完整加引號。遠端 GitHub repository 可另外使用英文名稱，例如 `discord-calculus-teaching-platform`。

## 最先交給 Codex

1. `CODEX_TASKS/00_START_HERE.md`
2. `CODEX_TASKS/BATCH_A_FOUNDATION.md`

Batch A 會先做環境診斷、monorepo、工具鏈、專案前言、架構決策、資料契約與假資料。完成後，再依 `CODEX_TASKS/TASK_MATRIX.md` 分流。

## 每一批都會留下

- 實作結果；
- 測試與 build 結果；
- 診斷問題；
- 假設與風險；
- 下一步建議；
- 可直接貼回 ChatGPT 討論的繁體中文摘要。

## 尚未授權 Codex 做的事情

- 建立或推送 GitHub remote；
- 公開部署 GitHub Pages；
- 建立／部署 Apps Script 雲端專案；
- 寄信；
- 連正式 Discord server；
- 使用真實學生資料；
- 讀取或要求真實 secrets。

## GitHub Pages 預設方向

既有的 `A-Cup-of-Chamomile-Tea-Latte.github.io` 保留。新專案使用另一個 repository 的 project site；Astro build 會預留 repository base path。


## 交接檔案列表

- `00_START_HERE.md`
- `01_SHARED_CONTEXT.md`
- `02_INITIAL_DIAGNOSTIC.md`
- `03_MONOREPO_SCAFFOLD.md`
- `04_TOOLCHAIN_QUALITY.md`
- `05_PROJECT_CHARTER_GLOSSARY.md`
- `06_ARCHITECTURE_DECISIONS.md`
- `07_DATA_CONTRACTS.md`
- `08_FIXTURES_MOCKS.md`
- `09_PORTAL_INFORMATION_ARCHITECTURE.md`
- `10_PORTAL_DESIGN_SYSTEM.md`
- `11_ASTRO_PORTAL_SCAFFOLD.md`
- `12_CASE_SEARCH_PROTOTYPE.md`
- `13_ONBOARDING_QUESTION_FORMS.md`
- `14_GITHUB_PAGES_PROJECT_SITE.md`
- `15_GAS_CLASP_SCAFFOLD.md`
- `16_SHEETS_SCHEMA_BOOTSTRAP.md`
- `17_GAS_CASE_API.md`
- `18_ACTIVATION_CODE_NONCE.md`
- `19_EMAIL_VERIFICATION_SKELETON.md`
- `20_MULTIBOT_ARCHITECTURE.md`
- `21_PYTHON_BOT_COMMON_CORE.md`
- `22_COURSE_ASSISTANT_BOT.md`
- `23_ARCHIVE_READER_BOT.md`
- `24_ANONYMOUS_MODAL_REPLY.md`
- `25_PRIVATE_SUPPORT_CASE.md`
- `26_LOCAL_EXPORT_PIPELINE.md`
- `27_ANONYMIZATION_CONSENT.md`
- `28_SHEETS_BATCH_IMPORTER.md`
- `29_SECURITY_PRIVACY_THREAT_MODEL.md`
- `30_TESTING_CI.md`
- `31_DOCUMENTATION_DEMO_PREFACE.md`
- `32_INTEGRATION_PLAN.md`
- `33_FINAL_DIAGNOSTIC_HANDOFF.md`
- `BATCH_A_FOUNDATION.md`
- `BATCH_B_PORTAL.md`
- `BATCH_C_GAS.md`
- `BATCH_D_BOTS.md`
- `BATCH_E_EXPORT.md`
- `BATCH_F_REVIEW.md`
- `TASK_MATRIX.md`
- `TEMPLATE_ADR.md`
- `TEMPLATE_TASK_REPORT.md`