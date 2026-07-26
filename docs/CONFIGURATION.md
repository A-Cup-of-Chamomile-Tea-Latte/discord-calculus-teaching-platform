# 設定總覽（M3）

最後核對：2026-07-26（以目前 source code 與 `.env.example` 為準）。本專案預設 fixture-first；沒有 component 會自動讀取 repository root 的 `.env`。若日後執行環境要載入檔案，必須由該 runtime／operator 明確載入，且不得提交檔案。

## 目前有效設定

| 範圍 | 實際讀取者 | 變數 | fixture 安全預設／規則 |
| --- | --- | --- | --- |
| Portal build | `apps/portal/astro.config.mjs` | `ASTRO_BASE_PATH` | 未設定或 `/` 時為 root；只影響 static build path。 |
| Portal build | `apps/portal/astro.config.mjs` | `ASTRO_SITE_URL` | optional；未設定不猜測正式網域。 |
| GAS runtime | `apps/gas/src/config.ts` 的 `PropertiesService` | `APP_ENVIRONMENT` | 未設定為 `fixture`。 |
| GAS runtime | 同上 | `FIXTURE_MODE` | 未設定為 `true`；只接受 `true`／`false`。 |
| GAS runtime | 同上 | `SPREADSHEET_ID` | `FIXTURE_MODE=false` 時必填；目前沒有正式 Sheet 可連。 |
| Course Assistant runtime | `bots/common/config.py` | `BOT_RUNTIME_MODE`、`COURSE_ASSISTANT_*` | fixture／dry-run 時 token 必須不存在；live 時才驗證 allowlisted IDs 與 token。 |
| Canonical `dump_bot` runtime（相容 namespace） | `bots/common/config.py`、`tools/discord_export` | `BOT_RUNTIME_MODE`、`ARCHIVE_READER_*` | 產品名稱已是 `dump_bot`；程式與部署變數暫保留 `ARCHIVE_READER_*`，不可另設第二組 token。live adapter 目前仍 fail closed。 |

## 範例檔的責任

- Root [`.env.example`](../.env.example) 只說明「root `.env` 不會被自動載入」；不要把各 component 的設定混放到一個檔案。
- [`apps/portal/.env.example`](../apps/portal/.env.example) 只列 Astro build variables。
- [`apps/gas/.env.example`](../apps/gas/.env.example) 是 PropertiesService 的文件化範例，不是 source runtime loader。
- [`bots/course_assistant/.env.example`](../bots/course_assistant/.env.example) 與 [`bots/archive_reader/.env.example`](../bots/archive_reader/.env.example) 分別說明互動 bot 與 reader compatibility runtime。`bots/.env.example` 只保留共同非 secret 的 mode。

## 已淘汰或尚未接線的名稱

下列舊範例名稱已移除，因目前 source 沒有讀取它們：`CASE_NUMBER_PREFIX`、`PORTAL_BASE_PATH`、`PUBLIC_CASE_API_URL`、`PUBLIC_SITE_BASE_PATH`、`DISCORD_OAUTH_CLIENT_ID`。案件編號由 case-ID service 產生；Portal 目前是 fixture static prototype，沒有 OAuth 或 live Case API。

`GAS_SCRIPT_ID`、`GAS_DEPLOYMENT_ID` 是日後 operator/deployment metadata，並非 `apps/gas/src/config.ts` 的 runtime input；它們保持空白且不得提交真實值。

## 安全規則

1. 不建立共享 production `.env`，尤其不得把 Course Assistant 和 `dump_bot` token 放在同一 runtime。
2. `BOT_RUNTIME_MODE=fixture`／`dry-run` 時，任何 bot token 都是設定錯誤；`live` 仍需要另行核准，且目前 reader live adapter 會拒絕連線。
3. `ASTRO_SITE_URL`、guild／channel ID、deployment ID 都不是秘密，但仍只應在需要它們的 component 設定；它們不代表 authorization。
4. 真實 token、credential、raw export、附件與學生資料一律維持 Git-ignored，不能出現在文件、report 或範例。

相關程式界線見 [Bot 架構](../bots/ARCHITECTURE.md)、[本機開發](architecture/DEVELOPMENT.md) 與 [尚未部署](DEPLOYMENT_NOT_DONE.md)。

