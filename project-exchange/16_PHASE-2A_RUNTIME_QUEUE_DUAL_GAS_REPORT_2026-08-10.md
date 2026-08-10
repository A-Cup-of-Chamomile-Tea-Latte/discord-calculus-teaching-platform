# Phase 2A — Canonical Runtime、Reliable Queue 與 Dual GAS 完工報告

日期：2026-08-10（Asia/Taipei）

完成時間：22:14

用途：GPT Pro 審閱／下一階段規劃

Canonical root：`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案`

> 本報告不含 Discord token、OAuth token、Script ID、Spreadsheet ID、deployment ID、
> Discord ID、學生姓名、Email 內容、Private Support 內容或 raw messages。

## 十分鐘結論

本輪已完成預定 Phase 2A 主線：先把髒 worktree 拆成可稽核 checkpoints，再將 live-tested
Discord runtime 納入 canonical tracked package；於 disposable SQLite 建立 checksum migration
ledger 與可靠 Private Support dump queue；最後把 GAS 拆成 standalone／bound 兩個共用 domain
的 target，推送到使用者指定的兩個既有空白 Apps Script project，逐 byte pull-back 驗證，並各自
建立 immutable version 1。

Standalone 另建立一個只有 owner 可存取的 fixture-only development Web App deployment；使用者
已在 Ding Ding profile 實測 `/health` 成功，確認 `status=200`、`fixtureMode=true`、
`discordGatewayHost=false`，且沒有擴大到公開或網域存取。Bound 不建立多餘 deployment：它在 `Server Database` 內透過
`onOpen` 加入「微積分模組管理」選單，第一次 dry-run／apply 保留給 Ding Ding Chrome profile
完成 Google 授權與人工確認。

兩隻既有 Discord bot 在 22:13 仍由原 LaunchAgent 執行，已連續運作約 11 天；本輪沒有 restart、
cutover、live SQLite migration 或 live export。換句話說：新 runtime/source/cloud infrastructure
已準備好，但不把 Discord live cutover 與 GAS deployment 綁成一次高風險切換。

## 完成範圍

### 1. Worktree 與 canonical source

- 將先前大量未提交成果拆成主題明確的 local commits。
- 建立 `runtime/discord-course-bots/`，納管兩隻已實機測試 bot 的 source、tests、文件與 package metadata。
- 明確排除 live `.env`、token、SQLite、exports、logs、PID、Discord resource mapping 與真實資料。
- 更新產品決策：Local SQLite 為 operational authority；Sheets 為行政 projection、分享與暫時復原層。
- 沒有 Git remote、沒有 GitHub push，也尚不需要建立 GitHub repository。

### 2. Versioned SQLite migration ledger

| Version | Purpose |
| --- | --- |
| 1 | baseline five runtime tables |
| 2 | legacy `base_title` 與 Private Support case number compatibility |
| 3 | Private dump claim／lease／attempt／retry／failure／updated metadata |

每個 migration 記錄 version、name、SHA-256 checksum 與 applied time，並同步
`PRAGMA user_version`。以下情況全部 fail closed：

- migration name 或 checksum 被竄改；
- DB 記錄比目前 runtime 更新的未知 migration；
- migration transaction 中途失敗。

重跑 idempotent，舊資料保留測試已通過；live DB 尚未被 version 3 runtime 開啟。

### 3. Reliable Private Support dump queue

```text
PENDING
  → BEGIN IMMEDIATE atomic claim
  → CLAIMED + unique token + worker ID + 15-minute lease
  → 5-minute heartbeat renews lease
  → selected closed channel export
  → manifest/checksum verification
  → current-token-only VERIFIED
```

- 暫時性錯誤：清除 claim，使用 bounded exponential backoff 回到 `PENDING`。
- 永久錯誤：進 `FAILED/PERMANENT`。
- 第五次仍失敗：進 `FAILED/EXHAUSTED`。
- lease 到期可由另一 worker 接手；舊 worker 的 token 不得完成或改寫新 claim。
- DB 只保存固定大寫 error code，不保存 exception 原文、訊息內容、姓名或附件資料。
- 每個 sweep 最多五個 jobs，避免單輪無界工作。

測試涵蓋雙 repository 同時搶單、lease reclaim、stale completion、heartbeat renewal、retry delay、
permanent failure、attempt exhaustion、安全 error code 與 v2→v3 legacy preservation。

### 4. Dual GAS architecture

| Target | Cloud container | Global entrypoints | Responsibility |
| --- | --- | --- | --- |
| standalone | `獨立 GAS` | `doGet`、`doPost`、bootstrap by configured ID | Web App/API、跨檔案操作 |
| bound | `Server Database` 附著 GAS | `onOpen`、dry-run、confirmed apply | Sheet UI／active spreadsheet 內部操作 |

兩個 target 從同一份 schema/domain source build，不各自手改 business rules。

Bound apply 的安全順序：

1. 先對 active spreadsheet 產生 dry-run actions；
2. 在 Sheet UI 顯示摘要；
3. 使用者選 Yes 才建立缺少的分頁、追加缺少欄位與更新受管 schema metadata；
4. 不刪除未知分頁、不移除既有欄位、不覆蓋 operator-owned rows。

### 5. Google Cloud actions

- 使用者已在 Google Apps Script settings 開啟 Apps Script API。
- clasp OAuth、兩個 cloud asset owner 與 Chrome Ding Ding profile 均確認包含同一專案帳號。
- Drive 工作範圍只限使用者指定的專案資料夾及其中的 `Server Database`、`獨立 GAS`。
- push 前分別 pull 至 gitignored inventory；兩邊都只有預設 `myFunction()` 與基礎 manifest。
- standalone 於 22:11:11 push；bound 於 22:11:39 push。
- 兩邊 push 後都 pull 至新的 gitignored verify directory，Code.js 與 manifest 逐 byte相同。
- 兩個 project 各建立 immutable version 1。
- standalone 建立 fixture-only、owner-only development Web App deployment。
- development `/health` 與 `Server Database` 已用 Chrome `Ding Ding` profile 開啟。
- 使用者回報 `/health` 成功：HTTP/application status 200、service `calculus-gas`、environment
  `fixture`、fixture mode true、Discord Gateway host false。
- 沒有 public/domain deployment、trigger、Email send、Sheet schema apply、Drive upload 或資料分析。

不使用 `clasp run` 執行 bound dry-run，原因不是程式失敗：Google 官方要求 API executable 與
caller 共用同一個 standard Cloud project；clasp 的 Google-provided OAuth client 與 Apps Script
預設 Cloud project 不符合。為一次 dry-run 新建額外 Cloud project／OAuth app 會增加無必要的
credential 與維運面，因此保留 Sheet UI 第一次授權。官方依據：
<https://developers.google.com/apps-script/api/how-tos/execute>

## Product decisions carried forward

- Local SQLite 是主要 operational authority；Sheets 是可寫的 administrative projection。
- Cloud → local fetch 必須檢查 schema/version、來源、時間與 checksum，再由人確認；不得靜默覆寫。
- Sheet-bound GAS 處理 active spreadsheet；standalone GAS 處理 Web App/API 與跨檔案事項。
- Email 的 `SENT` 只表示 approved sender call 成功且 audit 已寫入，不代表 inbox delivery/read。
- 學號、姓名與可回連學生身分的資料受保護；AI 分析需學生明確同意，且只限教學優化。
- 開發期直接覆蓋沒有相容價值的微小歷史；保留 migration、rollback 與外部操作 receipt。
- 此專案的人工瀏覽器操作固定使用 Chrome 顯示名稱 `Ding Ding` 的 profile；clasp 使用命名 OAuth profile `ntusupercool`。

## Verification summary

| Gate | Result |
| --- | --- |
| Secret scan | 569 candidate files，0 findings |
| Portal | 43 tests passed |
| Config Studio | 3 tests passed |
| GAS | 50 tests passed；standalone + bound build passed |
| Python | 205 tests passed |
| Runtime package | 37 tests passed；含 7 個 reliable queue scenarios |
| Type/lint/format | Astro 60 files 0 diagnostics；mypy 96 files；Ruff/Prettier/TS all pass |
| npm production audit | 0 vulnerabilities |
| npm development audit | 5 moderate，來自 clasp→googleapis→uuid；唯一自動完整修法會強制降 clasp 2.x，未採用 |
| Known warnings | 2 個既有 discord.py／Python 3.14 deprecation warnings |

### Push／pull-back fingerprints

| Target | File | SHA-256 | Pull-back |
| --- | --- | --- | --- |
| standalone | `Code.js` | `ab8f2188f11efebc592eb1b9ca8a3ade97400a87f90796886aea8b7b3778da28` | exact |
| standalone | `appsscript.json` | `7015e799ad4f0a4ae35febc5010ce7c6319a7261a202761bce9976518589a9b4` | exact |
| bound | `Code.js` | `716e5a3abcf38d4692a640477a0a667b337dd2c2832b8ac44bb8fe34051dae45` | exact |
| bound | `appsscript.json` | `7bae41361c73c9602bdf52f9fcea50a151191adde27ba4b76651849497504ae3` | exact |

## Git checkpoints

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
| `8ade3b6` | initial Phase 2A report checkpoint；本檔已依完工狀態整份覆寫 |

## Wall-clock timing

時間為可讀的約數；OAuth、測試與程式工作有部分重疊。21:15–22:03 是等待使用者回來與 Google
設定操作的外部停頓，不算 active implementation time。

| Node | Local time | Elapsed |
| --- | --- | ---: |
| dirty worktree inventory + scoped checkpoints | 20:43–20:49 | ~6 min |
| canonical runtime tracking + decisions | 20:49–20:53 | ~4 min |
| migration ledger | 20:53–20:55 | ~2 min |
| reliable queue implementation + tests + docs | 20:55–21:02 | ~7 min |
| clasp install/OAuth（與 queue 重疊） | 20:57–21:01 | ~4 min |
| dual GAS architecture/build/runbook | 21:02–21:12 | ~10 min |
| cloud inventory、API gate、初版報告 | 21:12–21:15 | ~3 min |
| external pause / user API setting | 21:15–22:03 | ~48 min wait |
| bound ID mapping、account proof、two pushes、pull-back、versions、deployment | 22:03–22:13 | ~10 min |

Active engineering／verification 約 42 分鐘；wall-clock 約 90 分鐘。

## Rollback and remaining boundaries

### Discord runtime

- live LaunchAgents 仍使用舊 runtime copy，因此本輪 code 不會直接改變線上 bot 行為。
- 正式 cutover 前：停止 worker → owner-only DB backup → 副本 migration/smoke → launcher path 切換 →
  health/queue verification → 保留舊 package 作一次 rollback。
- 不把 live DB migration 與 GAS deployment 放在同一 maintenance window。

### GAS

- 兩個 immutable version 1 是目前 rollback point。
- standalone deployment 只允許 owner；任何 access 擴大都需另行 privacy/security review。
- bound 尚未 apply Sheet schema；第一次操作先跑選單 dry-run，確認摘要後才 apply，再跑一次 dry-run
  應回報 no-op。
- Script ID、deployment ID、OAuth state 與 local project mapping 都在 gitignored local state，不進報告／Git。

## Recommended next work package

1. 在 Ding Ding profile 重新整理 `Server Database`，執行「檢查資料表結構（不修改）」。
2. 人工確認 dry-run 摘要後執行「套用資料表結構…」，再跑 dry-run 驗證 no-op。
3. 保持 standalone fixture mode；owner-only `/health` visual smoke 已完成。正式 Script Properties 留待
   下一個已核准的 adapter 工作包設定。
4. 建立 local→Sheets projection receipt：source commit、schema version、checksum、operator、timestamp。
5. 實作 cloud→local import gate：只允許 signed/hashed snapshot，驗證後仍需人工確認。
6. 另案實作 `CommandQueue`／`EmailQueue` adapters 與 triggers；Email `SENT` 語意保持 provider accepted。
7. 最後才做 Discord canonical runtime cutover；先處理 stale PID files 與 live DB backup/migration rehearsal。

## 想傳給 GPT Pro 的話

本輪不是 production launch，而是把 source、資料庫可靠性與 Google deployment boundary 收斂到可審核
狀態。請優先審：

1. Private dump claim/lease/retry terminal-state 是否足以作 reliable queue baseline；
2. local-primary、Sheets projection 的 authenticity receipt 是否應加入簽章或至少 HMAC；
3. standalone／bound GAS 的責任切割及 bound UI-confirmation 模型；
4. live runtime cutover 的 backup、rehearsal、rollback 與 monitoring gate；
5. Email、consent、Private Support 與 cloud backup 的 retention／access audit 規則。

請勿要求把 raw Discord messages、學生身分、Email、附件、Private Support、OAuth token、Script ID 或
deployment ID 上傳到聊天、LLM、Git、公開 ZIP 或公開網站。
