# Phase 2A — Canonical Runtime、Reliable Queue 與 Dual GAS Report

日期：2026-08-10（Asia/Taipei）  
用途：GPT Pro 審閱／下一階段決策  
Canonical root：`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案`

> 本報告不含 Discord token、OAuth token、Script ID、Spreadsheet ID、Discord ID、學生姓名、
> Email 內容、Private Support 內容或 raw messages。

## 十分鐘結論

1. 先前散落於 gitignored live runtime 的兩隻 Discord bot source 已建立 canonical tracked package；
   live LaunchAgent 尚未切換，因此本輪沒有中斷線上服務或遷移 live DB。
2. SQLite 已加入 checksum-verified migration ledger（v1–v3）。未知新版或 checksum 不符會
   fail closed；所有 migration 先在 disposable DB 驗證。
3. Private Support dump job 已從「每 10 秒掃 PENDING」升級為原子 claim、唯一 token、lease、
   heartbeat、bounded exponential retry、永久失敗／耗盡狀態與 stale-token protection。
4. GAS 已拆成共用 domain、兩個 entrypoint：standalone 負責 Web App/API；bound 負責
   `Server Database` 管理選單與人工確認的 schema dry-run/apply。
5. Google OAuth 與正確 Drive 工作目錄已確認；`獨立 GAS` 唯讀 pull 證明是預設空白 scaffold。
6. 雲端 push 目前尚未發生：Google 帳號層的 Apps Script API toggle 尚未生效。這是唯一
   standalone push blocker，不是程式錯誤。附著 GAS 仍需從母試算表編輯器取得其 Script ID。
7. 兩隻既有 bot 在報告建立時仍由 LaunchAgent 執行，PID 未變；本輪沒有 restart、cutover 或
   live SQLite open。

## 已接受的產品決策

- Local SQLite 是主要 operational authority；Sheets 是可寫的行政 projection、分享與暫時復原層。
- Cloud → local 不得靜默覆寫；先驗 schema/version、來源、時間、checksum，再由人確認。
- Sheet-bound GAS 處理 active spreadsheet 內部操作；standalone GAS 處理 Web App/API 與跨檔案事項。
- 兩個 GAS 共用 domain/schema source，不各自維護 business rules。
- Email 的 `SENT` 只表示 approved sender call 成功回傳且 audit 已寫入，不表示進 inbox 或已讀。
- 學號、姓名與可連回學生身分的資料受保護；AI 分析需學生明確同意，且只限教學優化用途。
- 開發期不保存無價值的細碎歷史；有相容價值的 migration 與 rollback 證據才保留。

## Local implementation

### Canonical runtime

- Package：`runtime/discord-course-bots/`
- Live source migration note：`runtime/discord-course-bots/SOURCE_MIGRATION.md`
- Console scripts：`course-assistant`、`dump-bot`、`discord-bot-invites`
- live `.env`、SQLite、exports、logs、PID 與 provisioning mapping 未進 Git。

### SQLite migration ledger

| Version | Purpose |
| --- | --- |
| 1 | baseline five runtime tables |
| 2 | legacy `base_title`、Private Support case number compatibility |
| 3 | Private dump claim／lease／attempt／retry／failure／updated metadata |

ledger 記錄 version、name、checksum、applied time，並同步 `PRAGMA user_version`。重跑 idempotent；
checksum tamper 與 newer unknown migration 都拒絕開啟。

### Reliable private dump queue

```text
PENDING
  → atomic BEGIN IMMEDIATE claim
  → CLAIMED + unique token + 15-minute lease
  → 5-minute heartbeat renews lease
  → export + manifest/hash verification
  → token-checked VERIFIED
```

- 暫時性錯誤：清除 claim，依 30s、60s、120s… bounded backoff 回到 `PENDING`。
- 永久錯誤：進 `FAILED/PERMANENT`。
- 第五次仍失敗：進 `FAILED/EXHAUSTED`。
- lease 過期可由另一 worker 接手；舊 token 不得 complete/fail 新 claim。
- DB 只保存固定大寫 error code，不保存 exception 原文或訊息內容。
- 每個 sweep 最多處理五個 job，避免單輪無界工作。

### Dual GAS build

| Build output | Global entrypoints | Responsibility |
| --- | --- | --- |
| `dist/standalone/` | `doGet`、`doPost`、bootstrap by configured ID | Web App/API、跨檔案 |
| `dist/bound/` | `onOpen`、dry-run、confirmed apply | `Server Database` UI／內部操作 |

Bound apply 先計算 dry-run 摘要，只有使用者在 Sheet UI 明確選 Yes 才建立缺少的分頁、追加缺少
欄位與更新受管 schema metadata；不提供 Web App route。

## Cloud evidence and current gate

- OAuth profile：owner 專用 Google 帳號，成功登入；credential 只在本機 clasp auth store。
- Drive scope：只確認使用者指定的專案資料夾、`Server Database` 與 `獨立 GAS`。
- `獨立 GAS` remote inventory：只有預設 `myFunction()` 與基礎 manifest；ignored inventory pull 成功。
- standalone local mapping：gitignored；Script ID 不進 Git／報告。
- first push：Google 在寫入前拒絕，原因為帳號層 Apps Script API 尚未 enable；remote 沒有變更。
- bound mapping：等待從 `Server Database` → Extensions → Apps Script 的編輯器 URL 取得既有 Script ID。
- 尚未建立 deployment、trigger、Email send、Sheet schema apply 或公開 URL。

## Verification

| Gate | Result |
| --- | --- |
| Secret scan | 568 candidate files，0 findings |
| Portal | 43 tests |
| Config Studio | 3 tests |
| GAS | 50 tests；standalone + bound build success |
| Python | 205 tests，2 個既有 discord.py/Python 3.14 deprecation warnings |
| Runtime package | 37 tests；含 7 個 reliable queue scenarios |
| Type/lint/format | Astro 60 files 0 diagnostics；mypy 96 files；Ruff/Prettier/TS all pass |
| npm production audit | 0 vulnerabilities |
| npm dev audit | 5 moderate，來自 clasp→googleapis→uuid；唯一建議修法會強制降 clasp 2.x，未採用 |

GAS bundle SHA-256：

- standalone：`ab8f2188f11efebc592eb1b9ca8a3ade97400a87f90796886aea8b7b3778da28`
- bound：`716e5a3abcf38d4692a640477a0a667b337dd2c2832b8ac44bb8fe34051dae45`

## Checkpoints

| Commit | Purpose |
| --- | --- |
| `ca14043` | review studio and live provisioning checkpoint |
| `b695807` | review experience and lifecycle guidance |
| `a0ed919` | GAS queues and repository evidence audit |
| `d53019a` | canonical tracked Discord runtime |
| `7911752` | versioned SQLite migration ledger |
| `e946e7a` | reliable Private Support dump jobs |
| `ab5337d` | bound + standalone GAS build targets |
| `9b4decb` | safe non-breaking clasp audit updates |

沒有 Git remote、沒有 push GitHub、沒有建立新 GitHub repository。

## Wall-clock timing（約數，平行工作會重疊）

| Node | Local time | Elapsed |
| --- | --- | ---: |
| worktree inventory + scoped checkpoints | 20:43–20:49 | ~6 min |
| canonical runtime tracking + decisions | 20:49–20:53 | ~4 min |
| migration ledger | 20:53–20:55 | ~2 min |
| reliable queue implementation + tests + docs | 20:55–21:02 | ~7 min |
| clasp install/OAuth（與 queue 工作重疊） | 20:57–21:01 | ~4 min |
| dual GAS architecture/build/runbook | 21:02–21:12 | ~10 min |
| Drive inventory、remote empty proof、cloud gate | 21:12–21:15 | ~3 min |

## Rollback／cutover boundary

- live bots 仍指向舊 runtime copy，所以回復本輪 code 只需不做 cutover；線上服務不受這些 commits 影響。
- live DB 未被 migration v3 開啟；正式 cutover 前必須停止 worker、建立 owner-only DB backup、在副本
  migration＋smoke，再一次性切 launcher path。
- GAS push 前保留 remote inventory；push 後先建立 immutable version。standalone deployment 預設
  `MYSELF`，未經另外核准不得擴大 access。
- Bound schema apply 先 dry-run 並由 Sheet UI 人工確認；cloud projection 不能反向靜默覆蓋 local。

## 下一步（依序）

1. 在 Apps Script 使用者設定開啟 API，等待 propagation 後 push standalone。
2. pull 回 ignored inventory，比對 Code.js／manifest SHA-256，建立 immutable version。
3. 從 `Server Database` 開啟附著 Apps Script，取得既有 Script ID；唯讀 pull 確認空白。
4. push bound target、pull-back verify、建立 immutable version。
5. 在 Sheet 先執行 dry-run；確認摘要後才 apply schema，apply 後再跑一次 dry-run 應為 no-op。
6. 另案設定 Script Properties、Web App development deployment、trigger／Email queue；不要在本輪直接公開。
7. 另案執行 live bot runtime cutover，不把它與 GAS deploy 綁成同一次不可逆操作。

## 想傳給 GPT Pro 的話

請把本輪視為「資料層與部署邊界收斂」，不是 production launch。最值得審的是：

1. reliable queue 的 claim/lease/retry terminal-state 是否足以作 Private dump baseline；
2. local-primary、Sheets projection 的真實性檢核是否需要 signed snapshot 或 operator receipt；
3. standalone／bound GAS 的責任切割是否接受；
4. live cutover 前還需要哪些 backup、rollback、quota 與 privacy gates。

請不要要求上傳 raw Discord messages、學生身分、Email、附件、Private Support 或 OAuth/Script ID。
