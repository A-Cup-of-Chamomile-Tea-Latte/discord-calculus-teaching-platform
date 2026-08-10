# Phase 2A — Runtime、SQLite、Reliable Queue 與 Compact Dual GAS 交接報告

日期：2026-08-10（Asia/Taipei）

最後更新：22:49

用途：GPT Pro 審閱／下一工作包裁決

Canonical root：`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案`

> 本報告不含 Discord／OAuth token、Script／Spreadsheet／deployment ID、學生姓名、學號、Email、Discord ID、Private Support、附件或 raw messages。

## Executive conclusion

Phase 2A 的可靠性主線可接受：canonical tracked Discord runtime、checksum-verified SQLite migration ledger、具 atomic claim／lease／heartbeat／retry 的 Private Support dump queue、standalone／bound 雙 GAS target 均已完成且集中驗證。

本次追加修正了 Google Sheet 過度正規化的 21-tab prototype。新版 schema 2.0.0 使用「local SQLite authority + compact cloud projection」：五個人類視圖、五個預設隱藏的 machine views。它不把 SQLite 複製到 Sheet，只投影 TA 真正需要的充分統計量、bot 健康狀態與低頻協作 metadata。

兩個 GAS project 已推送相同 domain build、pull-back fingerprint exact，並各建立 immutable version 3；standalone 既有 owner-only fixture deployment 已升至 v3。Bound compact migration code 已到雲端，最後一個 in-Sheet dry-run／Yes confirmation 由使用者在 Chrome `Ding Ding` profile 執行中；截至本次更新，未宣稱 Sheet 遷移已完成。

## Product architecture

| Layer | Authority / responsibility | Explicit exclusion |
| --- | --- | --- |
| Local SQLite | Bot operational state、transaction、queue、主要 authority | 不作遠端 dashboard |
| Google Sheets | 人可讀的 current projection、低頻 commands/outbox/sync receipts | raw message、完整 identity、secret、附件、完整 log |
| Git text | Schema、migration、policy、code、可 review 歷史 | live records、credential |
| Governed files | Raw/sanitized exports、attachments、manifest/checksum | 即時 operational state |
| Local rotating logs | 近期診斷 evidence | 永久 audit 或 TA view |

Cloud → local 永不以「雲端比較新」為理由靜默覆寫。未來 import gate 必須檢查 intended source、schema version、單調 source version、checksum、timestamp，並要求 operator confirmation。

## Compact Sheets schema 2.0.0

### 預設可見：給人看

| View | Sufficient statistics |
| --- | --- |
| `Overview` | 當前 KPI、警示、資料時間 |
| `CaseBoard` | 案件狀態、TA 待辦、期限、分析資格；無正文 |
| `Members` | opaque member ref、course alias、role、membership／verification status、analysis default；無姓名／學號／Email／Discord ID |
| `Operations` | 兩隻 bot、GAS、projection／queue 的 status、heartbeat、depth、safe error code；無 PID／log body |
| `History` | 重要 open／close／reopen／verification 等 lifecycle transitions；無高頻 event |

### 預設隱藏：給機器協作

| View | Boundary |
| --- | --- |
| `_CommandInbox` | idempotency、claim／lease／retry；只存 `payloadRef` |
| `_EmailOutbox` | metadata-only；`providerAcceptedAt` 對應產品 `SENT`，不代表 inbox delivery |
| `_SyncState` | source version、checksum、cursor、operator confirmation receipt |
| `_Artifacts` | index/checksum/retention；payload 留在 governed file carrier |
| `_Settings` | schema/data-authority receipts 與 non-secret config；禁止 secret value |

Hidden 是 UX，不是 security。若未來 TA 與 system operator 的讀者範圍不同，應依 access boundary 拆成兩份 Spreadsheet；目前不因頁籤數量任意拆檔。

## Safe v1.3 → v2.0 migration

Bound menu 已改為：

1. `檢查精簡資料庫遷移（不修改）`
2. `套用精簡資料庫遷移…`

Executable safety properties：

- allowlist 只包含 21 個精確舊受管名稱；
- 任一舊非-Settings tab 有 data row → actions 為空、零 mutation；
- 舊 `Settings` 出現 operator-owned key → actions 為空、零 mutation；
- 通過 preflight 才建立 10 個新頁、寫 v2 receipts、刪除空舊頁；
- unknown tab 永遠保留；
- second apply idempotent no-op；
- apply 後 machine views 隱藏，header 凍結、淺灰粗體、自動欄寬。

Local tests 覆蓋 safe apply、unknown preservation、legacy-data blocker、operator-setting blocker 與 no-op。雲端首次 apply 仍以 in-Sheet 結果為準。

## SQLite feasibility and transparency

SQLite 適合目前單機、兩隻 bot 共用的 operational state：不需另架 database server，支援 unique constraints、transactions、indexes 與可靠 migration。它不是 AI；所有 schema、SQL、migration 與 tests 都在 repository 可讀。

Canonical runtime 新增 `discord-db-inspect`：

- 以 SQLite read-only mode 開啟；
- 只報 schema version、table name、columns、row counts 與 database file SHA-256；
- 不執行 migration；
- 不 query／print application row values；
- 測試確認 inspector 前後主 database file hash 相同，且 synthetic private value 不出現在輸出。

教學路線已放在 `docs/guides/SQLITE_AND_DATA_CARRIERS_LEARNING_PATH.md`，分成 7 堂 15–30 分鐘的小課：資料地圖、唯讀 inspect、安全 SELECT、transaction/migration、queue、carrier decision、projection authenticity、backup/restore。每堂只用 synthetic/disposable DB，避免再次用大量文字製造理解債。

## Existing Phase 2A evidence retained

### SQLite migrations

| Version | Purpose |
| --- | --- |
| 1 | baseline five runtime tables |
| 2 | legacy `base_title` 與 Private Support case number compatibility |
| 3 | Private dump claim／lease／attempt／retry／failure／updated metadata |

Migration ledger 記錄 version、name、SHA-256 checksum、applied time 並同步 `PRAGMA user_version`；未知新版、name/checksum 不符或 transaction failure 全部 fail closed。Live SQLite 尚未由 canonical v3 runtime migration，live LaunchAgents 也尚未 cut over。

### Reliable Private Support queue

`PENDING → BEGIN IMMEDIATE claim → CLAIMED + unique token/worker/lease → heartbeat → export → manifest/checksum verify → VERIFIED`。

Temporary failure bounded backoff；permanent/exhausted failure terminal；expired lease 可 reclaim；stale token 不得完成新 claim；DB 只保存 safe error code，不保存 exception text 或內容。

### Dual GAS responsibility

| Target | Responsibility | Current cloud state |
| --- | --- | --- |
| standalone | owner-only fixture Web App/API、future cross-file orchestration | immutable v3；fixture deployment on v3 |
| bound | active `Server Database` menu、preflight、confirmed compact migration | immutable v3；awaiting operator menu apply receipt |

兩個 target 共用 domain/schema source，但 entrypoints 明確分開。所有 global handlers 是 explicit top-level function declarations，避免 Apps Script 不辨識 bundled `var` handler 的歷史問題。

## Verification

| Gate | Result |
| --- | --- |
| Secret scan | 572 candidate files，0 findings |
| Portal | 43 passed |
| Config Studio | 3 passed |
| GAS | 50 passed；TS/build passed |
| Python total | 206 passed；2 existing discord.py/Python 3.14 warnings |
| Canonical runtime subset | 38 passed |
| Static quality | Astro 60 files 0 diagnostics；mypy 96 files；Ruff/Prettier/TS passed |

### v3 push/pull-back fingerprints

| Target | File | SHA-256 | Pull-back |
| --- | --- | --- | --- |
| bound | `Code.js` | `030bd8aa3503e0e305134f66a10ffc57c6181d4dbd6e876bd9bcaf80d03ed257` | exact |
| bound | `appsscript.json` | `7bae41361c73c9602bdf52f9fcea50a151191adde27ba4b76651849497504ae3` | exact |
| standalone | `Code.js` | `27dd6f854a5c298be9810455bd1aac55c7e41f4c33be334cc054f0060b262162` | exact |
| standalone | `appsscript.json` | `7015e799ad4f0a4ae35febc5010ce7c6319a7261a202761bce9976518589a9b4` | exact |

## Git checkpoints

| Commit | Purpose |
| --- | --- |
| `7911752` | versioned SQLite migration ledger |
| `e946e7a` | reliable Private Support jobs |
| `ab5337d` | dual GAS build targets |
| `ffa138c` | explicit Apps Script handlers |
| `9178c0e` | compact cloud projection + safe migration + SQLite inspector + learning path |

## Timing

前段完整 wall-clock 與 OAuth 外部等待紀錄保留在 Git history。這次 compact redesign 節點：

| Node | Local time | Elapsed |
| --- | --- | ---: |
| 21-tab 問題辨識與 carrier decision | 22:23–22:31 | ~8 min discussion |
| compact schema、safe migration、fixtures/tests | 22:31–22:45 | ~14 min |
| docs、SQLite inspector、learning path | 22:45–22:48 | ~3 min |
| full repository gate | 22:48–22:49 | ~1 min active / ~15 sec command wall time |
| GAS v3 push、pull-back、version、standalone redeploy | 22:48–22:49 | ~1 min（與文件整理部分重疊） |

## Current boundaries / NO-GO

- Live bots 仍在既有 LaunchAgent/runtime；本輪未 restart 或 cutover。
- Live SQLite 未被 canonical migration/inspector 開啟。
- Standalone 保持 fixture + owner-only；沒有 public/domain access。
- 沒有寄信、trigger、real-data projection、cloud → local import、Discord command adapter 或 AI analysis。
- Bound cloud code已更新；Sheet apply 是否完成必須以使用者回報／second dry-run no-op 為 evidence。

## Recommended next work package

1. 完成 bound compact migration，保留 dry-run／apply／second dry-run no-op receipt。
2. 以 synthetic records 實作 local → Sheets projection adapter，只先寫 `Operations` 與 `Overview`。
3. 加上 authenticity receipt；再擴充 `CaseBoard`／`Members`，保持去識別欄位。
4. `_CommandInbox`／`_EmailOutbox` adapter 另案 integration test；Email `SENT` 只代表 sender responsibility complete。
5. 與使用者完成 SQLite 小課 1–2；再做 disposable backup/restore drill。
6. Discord live runtime cutover 另開 maintenance package：stop writer、owner-only backup、copy rehearsal、launcher switch、health/rollback。

## 請 GPT Pro 優先裁決

1. 10-view sufficient-statistics boundary 是否接受；哪些欄位仍可再刪？
2. Members 使用 opaque member ref + course alias 是否足夠，是否應完全移除 cloud member-level rows、只留 aggregate？
3. `Operations` heartbeat cadence／stale threshold 應如何定義，避免 Sheet 成為高頻 log？
4. Authenticity receipt 先用 SHA-256 + operator confirmation，或此階段就需要 HMAC/signature？
5. 何時因 access boundary 把 human console 與 machine ledger 拆檔？
6. SQLite 教學／inspector 是否足以降低黑盒風險，還需要哪一個最小 restore exercise？

請勿要求把 raw messages、學生身分、Email、附件、Private Support、OAuth token、Script／Spreadsheet／deployment ID 上傳到聊天、LLM、Git、公開 ZIP 或公開網站。
