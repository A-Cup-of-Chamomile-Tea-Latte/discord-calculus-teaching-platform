# 設定總覽

最後核對：2026-08-28。Production remote Linux 已運作 v13／schema 13；Portal 與 Email 尚未正式部署。設定名稱與責任以本頁和各 component 的 `.env.example` 為準，舊 Task report 只作歷史證據。

## Portal build

| 變數                               | 用途                              | 安全規則                                                                               |
| ---------------------------------- | --------------------------------- | -------------------------------------------------------------------------------------- |
| `ASTRO_BASE_PATH`                  | root 或 GitHub Pages project path | 未設定時為 `/`；只影響 static path                                                     |
| `ASTRO_SITE_URL`                   | 可選 public HTTPS origin          | 未設定不猜 production URL                                                              |
| `PUBLIC_PORTAL_BUILD`              | 建立 public artifact              | `build:public` 自動設為 `true`，並移除 internal routes／assets                         |
| `PUBLIC_JOIN_APPLICATION_ENDPOINT` | same-origin 加入申請 endpoint     | 未設定時 public submit fail closed；不得直連 SQLite、Bot token 或 GAS owner credential |
| `PUBLIC_CASE_STATUS_ENDPOINT`      | same-origin 單案狀態查詢 endpoint | 未設定時查詢 fail closed；只允許 content-free projection                               |
| `PUBLIC_PORTAL_SESSION_ENDPOINT`   | 匿名分 scope session endpoint     | 未設定時 join／lookup 都 fail closed；不得跨 scope 共用 session                        |

Backend、匿名分 scope session 與 synthetic staging 已通過本機驗證；正式 Portal service、HTTPS proxy、production SQLite 與 GAS 實寄尚未接線。預設 public build 不使用 fixture 冒充成功。

## Discord runtime

Canonical runtime：`runtime/discord-course-bots/`。`bots/` 下的 packages 是 fixture／歷史相容層，不是 production candidate。

### `.env`

- `COURSE_ASSISTANT_TOKEN`、`COURSE_ASSISTANT_CLIENT_ID`
- `DUMP_BOT_TOKEN`、`DUMP_BOT_CLIENT_ID`
- `TEST_GUILD_ID`、`BOT_OWNER_IDS`
- `DATABASE_PATH`、`LOG_LEVEL`
- `DRAFT_REMINDER_SECONDS`、`DRAFT_DELETE_SECONDS`
- `CASE_IDLE_SECONDS`、`CASE_AUTO_CLOSE_SECONDS`
- `PRIVATE_OPEN_CAPACITY`
- `TEST_MODULE_CODE` 只作受限 fallback；公開案件的 Module 必須由 class mapping 取得

Token、owner IDs 與 live DB path 只放 host secret boundary，不進 Git、文件、聊天或 public artifact。

### SQLite `runtime_config`

以下只保存 Discord resource mapping，不保存 token 或學生內容：

- `managed_forum_ids`、`private_support_category_id`、`private_support_entry_channel_id`
- `course_role_id`、`visitor_role_id`
- `ta_role_id`、`professor_role_id`、`system_admin_role_id`
- `class_role_01` 至 `class_role_16`
- `class_module_01` 至 `class_module_16`

System admin 透過 allowlisted `/join-admin set-role`、`set-category`、`set-module`、`add-forum` 與 `remove-forum` 維護。不要用任意 key/value slash command，也不要把直接 SQL 當日常 UI。設定完成後仍須以白帳號驗證 role hierarchy、唯一班別、Private ACL 與 115-1 canonical mapping。

第一位 Bot system admin 由 Discord guild owner／`BOT_OWNER_IDS` bootstrap；Portal `/access/` 的本機帳號是 reviewer UI 展示層，兩者不是同一套 production credential。

## GAS／Sheets

Standalone GAS 維持 owner-only Execution API，無 public Web App。主要 Script Properties：

- `BRIDGE_SPREADSHEET_ID`、`BRIDGE_SPREADSHEET_FINGERPRINT`
- `BRIDGE_ENVIRONMENT`、`BRIDGE_SYNTHETIC_ONLY`
- 舊 `PHASE2B_*` 只作相容 fallback

Bound status digest 另使用 `STATUS_EMAIL_RECIPIENTS`、`STATUS_SPREADSHEET_ID`；是否啟用是獨立 gate，不因 source 存在而自動開啟。

## Academic config

115-1 canonical data：`config/academic/115-1/course-operations.yaml`。它是 active class、class→Module、教師與 TA 對照的 repository authority；Discord snowflake mapping 仍留在 `runtime_config`，不可回寫到公開 academic source。

## 本機 Portal access

`/access/` 只供 reviewer build 的本機審查：帳號以 salted hash lookup，密碼使用 PBKDF2 verifier，session 存於 browser session storage。它不是正式伺服器端 AuthN／AuthZ，public artifact 會移除該路由。正式 backend 上線前不得把這層當 production 保護。

## 固定安全規則

1. 不建立共享 production `.env`；兩隻 Bot token 分開管理。
2. Browser 永不持有 Bot token、Google owner credential 或 SQLite write access。
3. Guild／channel／role ID 不是 secret，但仍只放必要的受限設定；不把真人 ID 貼入交接或公開文件。
4. 真實 token、credential、raw export、附件與學生資料一律維持 Git-ignored。
5. candidate config 或 migration 在獨立副本驗證後，仍須另行明示授權才可 forward production。

相關入口：[Bot runtime README](../runtime/discord-course-bots/README.md)、[實作狀態](IMPLEMENTATION_STATUS.md)、[架構概觀](architecture/OVERVIEW.md)與[部署邊界](DEPLOYMENT_NOT_DONE.md)。
