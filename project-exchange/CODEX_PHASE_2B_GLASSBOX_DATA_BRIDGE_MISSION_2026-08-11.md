# Codex Mission：Phase 2B 透明資料聯動實驗室

日期：2026-08-11  
基線 commit：`e8555e8`  
任務性質：**架構決策已凍結，Codex 主要負責實裝、測試與交接**  
預期工作時間：單一大型工作包；以局部測試推進，最後只跑一次整合驗證

## 0. 任務依據與權威順序

開始前精準閱讀：

1. `project-exchange/16_PHASE-2A_RUNTIME_QUEUE_DUAL_GAS_REPORT_2026-08-10.md`
2. `SHEETS_SCHEMA.md`
3. canonical runtime 的 repository／service／migration／queue 實作
4. GAS compact schema 2.0.0、bound／standalone entrypoints 與相關測試
5. SQLite 唯讀 inspector 與現有教學文件

發生衝突時，依下列順序處理：

1. 現行 canonical 決策文件與 `SHEETS_SCHEMA.md`
2. 本任務明確凍結的決策
3. 現有 canonical code style 與既有抽象

不得自行建立新的產品規則。若現有程式與本任務無法相容，停止該 Gate，保留其他安全成果，並以具體 path／symbol／test 證據回報。

---

# 一、任務目標

建立一套 **staging-only、synthetic-only、逐步人工觸發** 的資料聯動實驗室，讓使用者可以親自看到：

```text
本機來源：
假 Discord／Bot 事件
→ canonical local program
→ staging SQLite
→ projection outbox
→ GAS
→ Google Sheets

雲端來源：
Google Sheet 的資料聯動實驗室
→ _CommandInbox
→ local bridge fetch
→ validation
→ staging SQLite
→ projection outbox
→ Google Sheets receipt／人類視圖
```

必須證明：

1. SQLite 仍是 operational authority。
2. `CaseBoard`、`Overview`、`History` 等人類視圖不會被下載後覆寫 SQLite。
3. Cloud → Local 只能經 `_CommandInbox` 的明確命令封包。
4. 每一步都可以 dry-run、人工確認、apply、查看 receipt。
5. 重複命令不會重複執行。
6. checksum、版本、環境或來源錯誤時，SQLite 與 Cloud 都不應被錯誤修改。
7. 本任務完成後，使用者能實際輸入假案件，逐層檢查結果。

---

# 二、已凍結的架構決策

Codex 不需也不得重新裁決以下事項。

## 2.1 Authority

- **Local SQLite**：案件與 queue 的唯一操作真相。
- **Google Sheets**：人類可讀投影、低頻命令入口與同步收據。
- **GAS**：Google 端的驗證、鎖定、preview／apply 與 Sheet 寫入層。
- **CaseBoard／Overview／History／Operations**：只出不進，永遠不是 Local command source。
- **`_CommandInbox`**：唯一 Cloud → Local 入口。
- **`_SyncState`**：只保存 cursor／checksum／receipt，不保存案件真相。

## 2.2 本任務不做背景常駐同步

本任務所有流程均為 one-shot CLI 或 Sheet menu／sidebar 人工觸發：

- 不建立 daemon。
- 不建立 LaunchAgent。
- 不建立 Apps Script clock trigger。
- 不自動輪詢。
- 不碰 live runtime。

完成透明實驗後，才另案決定 production scheduler。

## 2.3 Production 預設同步策略（只做設定與測試，預設停用）

為避免日後再次討論，先固定建議預設值；本任務不得啟用背景執行：

| 項目 | 預設值 | 規則 |
|---|---:|---|
| Local SQLite 寫入 | 事件發生時立即 | 只寫本機 transaction，不在 Discord handler 內等待 Google |
| Projection flush interval | 60 秒 | 未啟用；未來由單一 worker 執行 |
| Projection threshold | 20 個 pending events | 達門檻可提前 flush |
| Projection batch maximum | 50 個 events | 超過分批，避免大型單次 payload |
| Cloud command poll | 60 秒 | 未啟用；未來只有單一 consumer |
| Local component heartbeat | 60 秒 | 只寫本機最新狀態，不保留高頻歷史 |
| Operations cloud publish | 300 秒 | 或 component／queue 狀態改變時立即投影一次 |
| Operations stale threshold | 900 秒 | 15 分鐘未更新標示 stale |
| Critical stale threshold | 1800 秒 | 30 分鐘未更新標示 critical |
| Concurrent projection worker | 1 | 不允許多 worker 同時寫同一 Spreadsheet |
| Concurrent command consumer | 1 | 由 claim／lease 保護 |

額外規則：

- 不得每則 Discord message 都呼叫 Google。
- 同一 case 的多個 pending current-state projection 可合併，只保留最新狀態。
- `History` lifecycle event 不合併，維持 append-only。
- `Operations` heartbeat 在 Sheet 中覆寫最新值，不建立高頻 heartbeat log。
- 外部 API 失敗不得阻塞 Discord event handler；只留下 durable local work。

## 2.4 固定資料範圍

本任務只投影：

- `Overview`
- `CaseBoard`
- `Operations`
- `History`
- `_SyncState`

本任務不碰：

- `Members`
- `_EmailOutbox`
- `_Artifacts` payload
- 真實 `_CommandInbox` Discord 操作
- raw archive
- Private Support
- 附件
- 真實身份

## 2.5 Synthetic 規則

- 所有假案件使用 `TST-` 前綴。
- 所有假 command 使用 `CMD-TST-` 前綴。
- 所有假 internal identity 使用 `SYN-` 前綴，且不得模仿 Discord snowflake。
- `analysisEligible` 永遠為 `false`。
- 不保存姓名、學號、Email、Discord ID、message body、附件、filename 或 Private Support。

---

# 三、使用者與 Codex 分工

## 使用者只負責

1. 若 bound Sheet migration receipt 尚未完成：
   - 執行 dry-run。
   - 無 blocker 才 apply。
   - 再執行一次 dry-run，確認 no-op。
2. 若需要新 OAuth：只做一次 Google 帳號點選授權。
3. 按照完成後的 walkthrough：
   - 在 Sheet 選 fixture command。
   - 在 terminal 執行 Codex 提供的單行命令。
   - 核對 dry-run、apply 與各層 receipt。

使用者不需：

- 審核 SQL 實作。
- 決定 table／status／command 名稱。
- 決定同步頻率。
- 決定 transport fallback。
- 逐一閱讀所有測試。

## Codex 負責

- migration、schema、repository、service adapter、GAS functions、CLI、tests、guide、report。
- 依本任務的固定決策實作。
- 不以問題把產品決策丟回使用者。
- 只有遇到強制停止條件時，才回報精確 blocker。

Codex 可自行決定的範圍僅限：

- 符合既有 repository 慣例的檔案位置。
- 私有 helper／class／function 名稱。
- 測試 fixture 的非語意細節。
- 不改變契約的內部重構。

---

# 四、不可跨越的 NO-GO

- 不啟動、停止或修改 live Bot／LaunchAgent。
- 不開啟、inspect、migration 或複製 live SQLite。
- 不連接真實 Discord Gateway。
- 不執行 Discord write。
- 不寄 Email。
- 不建立正式 Drive archive。
- 不輸入或投影真實學生資料。
- 不讀取 `.env`、Discord token、OAuth token 內容、raw dump 或附件。
- 不把 credential、Script ID、Spreadsheet ID、Deployment ID 寫入 Git／report／log。
- 不讓 Cloud row 直接覆寫 SQLite。
- 不加入 Portal 功能或做網站維護。
- 不更新正式 Project Knowledge。
- 不 push remote。
- 不做 unrelated refactor。
- 不新增背景 scheduler。

---

# 五、工作分解與固定實作規格

## Gate 0 — 基線與工作 branch

1. 確認 canonical root。
2. 確認 HEAD 可追溯到 `e8555e8`。
3. `git status` 必須乾淨；否則停止修改並回報。
4. 記錄 branch、HEAD、Node、Python、SQLite、clasp 版本。
5. 建立：

```text
codex/phase-2b-glassbox-data-bridge
```

不得 push。

## Gate 1 — Bound Sheet migration receipt

檢查是否已有：

1. compact migration dry-run receipt
2. apply receipt
3. second dry-run no-op receipt

若完整，記錄 safe fingerprint，不輸出完整 ID。

若不完整：

- Local implementation 繼續。
- 所有真正 cloud mutation 保持 blocked。
- 最終只要求使用者完成這三步。
- 不得人工刪除 Sheet 繞過 blocker。

## Gate 2 — Staging carrier

建立 ignored local carrier：

```text
.local/phase2b-data-lab/
├── staging.sqlite3
├── staging-config.json
├── receipts/
└── projection-bundles/
```

規則：

- 整個路徑必須被 Git ignore。
- `staging-config.json` 不保存 OAuth token；只保存 non-secret local mapping。
- staging DB 必須由 canonical migration framework 建立。
- `runtime_config` 必須包含：

```text
environment = STAGING
synthetic_only = 1
live_discord_enabled = 0
```

任何偵測到 production／live marker 的操作都 fail closed。

## Gate 3 — SQLite migration v4

不得修改既有 migration bytes。

新增 migration v4，固定建立以下四張表。

### 3.1 `case_lifecycle_events`

| Column | Requirement |
|---|---|
| `event_id` | TEXT primary key |
| `case_id` | TEXT not null |
| `case_ref` | TEXT not null，synthetic 必須 `TST-` |
| `event_type` | `OPEN`／`CLOSE`／`REOPEN` |
| `previous_status` | nullable TEXT |
| `new_status` | TEXT not null |
| `source_kind` | `LOCAL_FIXTURE`／`CLOUD_COMMAND` |
| `correlation_id` | TEXT not null |
| `occurred_at` | UTC ISO-8601 TEXT |
| `synthetic` | INTEGER CHECK 0/1，必須 1 |

必要 index：`case_ref, occurred_at`。

### 3.2 `inbound_commands`

| Column | Requirement |
|---|---|
| `command_id` | TEXT primary key，必須 `CMD-TST-` |
| `idempotency_key` | TEXT unique not null |
| `command_type` | allowlist command type |
| `payload_ref` | allowlist fixture URI |
| `target_case_ref` | nullable TEXT |
| `source_version` | INTEGER not null |
| `envelope_sha256` | 64-char lowercase hex |
| `source_fingerprint` | TEXT not null |
| `status` | `FETCHED`／`VALIDATED`／`APPLIED`／`REJECTED` |
| `fetched_at` | UTC timestamp |
| `validated_at` | nullable |
| `applied_at` | nullable |
| `rejected_at` | nullable |
| `result_code` | nullable safe code |
| `updated_at` | UTC timestamp |

### 3.3 `projection_outbox`

| Column | Requirement |
|---|---|
| `projection_id` | TEXT primary key |
| `aggregate_type` | 固定 `PUBLIC_CASE`／`OPERATIONS` |
| `aggregate_ref` | TEXT not null |
| `event_type` | `UPSERT_CURRENT_STATE`／`APPEND_HISTORY`／`UPDATE_OPERATIONS` |
| `projection_scope` | `OVERVIEW`／`CASEBOARD`／`HISTORY`／`OPERATIONS` |
| `source_version` | INTEGER not null |
| `payload_sha256` | nullable，建立 envelope 後填入 |
| `status` | `PENDING`／`CLAIMED`／`COMPLETED`／`RETRYABLE_FAILURE`／`PERMANENT_FAILURE` |
| `attempt_count` | INTEGER default 0 |
| `next_attempt_at` | nullable UTC timestamp |
| `claimed_by` | nullable TEXT |
| `claim_token` | nullable TEXT |
| `lease_expires_at` | nullable UTC timestamp |
| `last_error_code` | nullable safe code |
| `created_at` | UTC timestamp |
| `updated_at` | UTC timestamp |
| `completed_at` | nullable UTC timestamp |

重用現有 reliable Private queue 的 atomic claim、lease、stale-token rejection、bounded retry 實作；不要另發明第二套 queue engine。

### 3.4 `sync_state`

| Column | Requirement |
|---|---|
| `stream_name` | TEXT primary key |
| `last_remote_source_version` | INTEGER not null default 0 |
| `last_remote_checksum` | nullable TEXT |
| `last_local_projection_version` | INTEGER not null default 0 |
| `last_local_projection_checksum` | nullable TEXT |
| `last_success_at` | nullable UTC timestamp |
| `receipt_ref` | nullable safe opaque ref |
| `updated_at` | UTC timestamp |

固定 stream：

- `cloud-command-inbox`
- `local-sheet-projection`

### 3.5 Migration tests

必須覆蓋：

- empty DB → v4
- v3 → v4
- existing data preserved
- repeated migration no-op
- checksum／name mismatch fail closed
- unknown newer DB fail closed
- transaction failure rollback
- live DB path refusal

只可使用 disposable DB。

## Gate 4 — Fixture catalog 與 canonical envelopes

### 4.1 Fixture catalog

固定提供：

```text
fixture://public/basic-v1
fixture://public/close-reopen-v1
fixture://failure/stale-version-v1
fixture://failure/bad-checksum-v1
```

Fixture 只可包含：

- synthetic opaque case ref
- module
- keyword
- lifecycle status
- TA action
- synthetic UTC timestamps
- optional deadline
- reopen count
- `analysisEligible = false`

### 4.2 Command type allowlist

```text
CREATE_SYNTHETIC_CASE
CLOSE_SYNTHETIC_CASE
REOPEN_SYNTHETIC_CASE
REPLAY_LAST_SYNTHETIC_COMMAND
```

`SUBMIT_STALE_VERSION_FIXTURE` 與 `SUBMIT_BAD_CHECKSUM_FIXTURE` 是 UI 測試動作，不是合法 local command type；它們必須在 validation 層被拒絕。

### 4.3 Canonical JSON 規格

不新增第三方 canonicalization dependency，除非 repository 已存在。

固定規則：

- UTF-8
- object keys lexicographic sort
- compact separators
- no insignificant whitespace
- timestamps 正規化為 UTC `Z`
- 禁止 floating-point 欄位
- checksum 計算時排除 `checksum` 欄位本身
- SHA-256 lowercase hex

### 4.4 Command envelope

```json
{
  "schemaVersion": "2.0.0",
  "environment": "STAGING",
  "syntheticOnly": true,
  "commandId": "CMD-TST-...",
  "commandType": "CREATE_SYNTHETIC_CASE",
  "payloadRef": "fixture://public/basic-v1",
  "targetCaseRef": null,
  "idempotencyKey": "...",
  "sourceVersion": 1,
  "requestedAt": "2026-08-11T00:00:00Z",
  "sourceFingerprint": "...",
  "checksum": "..."
}
```

### 4.5 Projection envelope

固定結構：

```json
{
  "schemaVersion": "2.0.0",
  "environment": "STAGING",
  "syntheticOnly": true,
  "sourceVersion": 1,
  "generatedAt": "2026-08-11T00:00:00Z",
  "sourceFingerprint": "...",
  "scopes": ["Overview", "CaseBoard", "Operations", "History"],
  "rowCounts": {},
  "rows": {},
  "checksum": "..."
}
```

Projection 內容必須符合既有 compact Sheet v2.0.0 欄位；不得更改 Sheet schema。

## Gate 5 — Synthetic local ingest

建立 synthetic event adapter，但不得直接以 CLI 任意 SQL insert。

固定路徑：

```text
fixture／wizard
→ canonical validation
→ canonical service
→ canonical repository transaction
→ cases
→ case_lifecycle_events
→ projection_outbox
```

同一筆 SQLite transaction 中：

1. 建立／更新 synthetic case。
2. 寫入 lifecycle event。
3. 建立 projection outbox work。

任一步失敗全部 rollback。

建立 CLI：

```text
discord-data-lab create-case --interactive
discord-data-lab ingest --fixture <fixture-ref> --dry-run
discord-data-lab ingest --fixture <fixture-ref> --apply --confirm <nonce>
discord-data-lab case-status --case-ref <TST-ref>
discord-data-lab inspect --run-id <id>
```

Interactive wizard 只可輸入：

- module
- keyword
- initial lifecycle state
- TA action
- optional synthetic deadline

Dry-run 必須：

- DB SHA-256 前後相同。
- 顯示 planned transition。
- 顯示預計產生的 outbox scope。
- 不輸出 SQL row dump。

## Gate 6 — Cloud transport（固定決策樹）

不得自行選擇新的 auth architecture。

依序執行：

### A. 優先使用現有 standalone GAS owner-only API transport

若 repository 已有可由本機安全呼叫的 authenticated adapter，直接重用。

### B. 若沒有現成 adapter，但現有 clasp profile 可執行 Apps Script API function

允許將 **standalone target** 建立為 staging API executable，並以已登入的 named clasp profile 執行 remote function。

規則：

- 只作本次互動式 staging lab transport。
- local program 不得讀取或解析 `.clasprc.json`。
- 不得把 clasp token 當 production runtime credential。
- 不建立 public web endpoint。
- 不擴大到真實資料 scope。

### C. 若 A、B 均不可行

- 完成 local adapter interface、GAS functions、fake transport 與全部 local tests。
- 停止真正 cloud smoke test。
- 回報精確 blocker。
- 不得改用 service account、公開 web app、shared secret 或直接把 token 寫入 config。

### Target responsibility

- **Bound GAS**：Sheet menu／sidebar 與 compact Sheet 操作。
- **Standalone GAS**：staging API function、preview／apply／claim／ack orchestration。
- Standalone 透過受保護的 Script Property 取得 bound Spreadsheet reference；不得寫入 Git／report。

## Gate 7 — Local → Cloud projection

固定只更新：

- `Overview`
- `CaseBoard`
- `Operations`
- `History`
- `_SyncState`

流程：

1. atomic claim `projection_outbox`。
2. current-state event 依 `aggregate_ref + projection_scope` coalesce，只保留最新版本。
3. History append event 不 coalesce。
4. 建 canonical projection envelope。
5. 計算 checksum。
6. 呼叫 GAS preview。
7. GAS 驗證 schema／environment／fingerprint／version／checksum。
8. GAS 回傳 diff summary + confirmation nonce。
9. dry-run 停止，Cloud 零 mutation。
10. apply 必須帶同一 envelope + nonce。
11. GAS 使用 ScriptLock。
12. 先寫人類 views，最後寫 `_SyncState` success receipt。
13. local 收到 success receipt 後才將 outbox 標為 `COMPLETED`。

固定衝突規則：

- 相同 source version + 相同 checksum → no-op success。
- 相同 source version + 不同 checksum → reject `SYNC_VERSION_CHECKSUM_CONFLICT`。
- source version 倒退 → reject `SYNC_STALE_VERSION`。
- Spreadsheet fingerprint 錯 → reject `SYNC_WRONG_TARGET`。
- partial write 沒有 success receipt → local 保留 retryable work。

建立 CLI：

```text
discord-data-bridge project --once --dry-run
discord-data-bridge project --once --apply --confirm <nonce>
discord-data-bridge projection-status
```

## Gate 8 — Cloud → Local fixture commands

Bound Sheet 新增：

```text
微積分模組管理
└── 資料聯動實驗室
```

使用 sidebar 或 dialog；不得提供任意 JSON textarea。

固定 UI 動作：

- 建立基本假案件
- 關閉指定假案件
- 重開指定假案件
- 重送上一筆假命令
- 提交 stale-version 測試
- 提交 bad-checksum 測試

Sidebar 必須顯示：

- `STAGING／SYNTHETIC ONLY`
- 不操作 Discord
- 不碰 live DB
- 這次會建立哪種 command
- 下一步應執行的 local CLI

Cloud command row 由 GAS 產生，並使用 ScriptLock／claim token／lease。

建立 local CLI：

```text
discord-data-bridge fetch --once --dry-run
discord-data-bridge fetch --once --apply --confirm <nonce>
discord-data-bridge command-status --command-id <id>
```

Local validation 固定順序：

1. source fingerprint
2. schema version
3. environment = STAGING
4. syntheticOnly = true
5. source version monotonic
6. checksum
7. command type allowlist
8. fixture payloadRef allowlist
9. operator confirmation
10. idempotency key

Apply 固定順序：

1. 將 command 寫入 `inbound_commands`。
2. validation 成功改為 `VALIDATED`。
3. 經 canonical service 改變 staging case。
4. 同 transaction 寫 lifecycle event 與 projection outbox。
5. local commit 後改為 `APPLIED`。
6. 最後 remote ack。

若 local commit 成功但 remote ack 失敗：

- 下次依 command ID／idempotency key 回傳既有結果。
- 不得再次執行 lifecycle transition。

人類視圖 row 永遠不得被 fetcher 讀作 command。

## Gate 9 — Observer 與使用者手冊

`discord-data-lab inspect --run-id <id>` 固定輸出：

1. Cloud command
2. Local fetch／validation
3. Local inbound ledger
4. Synthetic case state
5. Projection outbox
6. Cloud projection receipt
7. Final human-view state

每段只顯示：

- status
- source version
- abbreviated checksum
- timestamp
- safe result code
- next expected action

建立：

```text
docs/guides/PHASE_2B_GLASSBOX_DATA_LAB.md
```

必須以操作清單寫成：

- 我現在按什麼
- 我在哪裡看到結果
- 正常時應該看到什麼
- 異常代表哪一層出問題
- 下一條命令是什麼

不要只寫抽象架構。

---

# 六、固定使用者 walkthrough

## Experiment A — Local origin

1. ingest dry-run。
2. 驗證 DB hash 不變。
3. apply basic fixture。
4. inspector 應看到：
   - schema v4
   - cases +1
   - lifecycle events +1
   - projection outbox pending
5. projection dry-run。
6. 查看 Overview／CaseBoard／Operations／History diff。
7. projection apply。
8. Sheet 應看到：
   - CaseBoard 的 `TST-` row
   - Overview count 更新
   - History OPEN event
   - Operations latest sync
   - `_SyncState` receipt

## Experiment B — Cloud origin

1. 在 sidebar 選 CLOSE。
2. `_CommandInbox` 出現 `QUEUED`。
3. local fetch dry-run。
4. DB hash 不變。
5. local fetch apply。
6. staging case 變 `CLOSED`。
7. projection apply。
8. Sheet CaseBoard 變 `CLOSED`。
9. History 新增 CLOSE event。
10. `_CommandInbox` 顯示完成 receipt。

## Experiment C — Idempotency

1. 重送同一命令。
2. local ledger 找到相同 idempotency key。
3. status／reopen_count 不得再次改變。
4. remote 顯示 no-op／same result。

## Experiment D — Rejection

1. 在 sidebar 提交 bad-checksum 測試。
2. local fetch 拒絕。
3. DB hash 不變。
4. projection outbox 不增加。
5. Sheet 顯示 safe rejection code。

---

# 七、固定 failure tests

至少覆蓋：

- duplicate command ID
- duplicate idempotency key
- same idempotency key with different payloadRef
- stale source version
- source version rollback
- bad checksum
- wrong Spreadsheet fingerprint
- wrong environment
- non-synthetic command
- unsupported command type
- expired remote claim
- stale remote claim token
- crash after fetch before local commit
- crash after local commit before remote ack
- crash after local commit before projection
- duplicate projection delivery
- same projection version + same checksum no-op
- same projection version + different checksum rejection
- partial Sheet write without success receipt
- direct edit of CaseBoard ignored
- direct edit of Overview ignored
- live DB path refusal
- live Discord disabled
- receipt leakage scan
- local dry-run DB hash unchanged
- cloud dry-run zero mutation
- projection batch max 50
- same-case current-state coalescing
- History append event not coalesced

每個測試需斷言：

- 哪層拒絕
- SQLite 是否改變
- Cloud 是否改變
- retry 是否安全
- 使用者看到的 safe error code

---

# 八、quota 與測試策略

- 每個 Gate 只跑 relevant targeted tests。
- 不反覆跑 full repository suite。
- 不掃描無關 Portal／NAP／分析模組。
- 不修改 Portal；正常情況不執行 Portal tests。
- 不升級 unrelated dependency。
- 優先重用既有 queue、canonical JSON、GAS adapter 與 test helpers。
- 新 dependency 必須必要、鎖版並在報告說明。
- 全部完成後只跑一次 final integration gate。

Final gate 至少包括：

- canonical runtime targeted／integration tests
- migration v4 tests
- bridge tests
- GAS tests／typecheck／build
- contract tests
- formatter／linter／typecheck for modified packages
- secret scan
- `git diff --check`

---

# 九、Git 與交接

建議 scoped commits：

1. `feat(runtime): add phase2b migration and contracts`
2. `feat(runtime): add synthetic ingest and projection outbox`
3. `feat(gas): add staging data lab and bridge functions`
4. `feat(bridge): add one-shot fetch project and observer`
5. `test(datalab): cover round-trip and failure recovery`
6. `docs: add glass-box walkthrough and handoff`

不得 push。

更新：

- `docs/IMPLEMENTATION_STATUS.md`
  - 修正 Portal tests `49 → 53`
  - 記錄 Phase 2A complete
  - 記錄 Phase 2B synthetic bridge 的實際完成範圍
- `docs/NEXT_STEPS.md`

不要更新正式 Project Knowledge。

建立唯一主報告：

```text
project-exchange/17_PHASE_2B_GLASSBOX_DATA_BRIDGE_REPORT_2026-08-11.md
```

報告開頭必須有「十分鐘白話版」，回答：

1. 真正資料流是什麼？
2. 為何 CaseBoard 不會覆寫 SQLite？
3. 假案件從哪裡進入？
4. SQLite 何時改變？
5. Cloud 何時改變？
6. checksum／version／confirmation 各在防什麼？
7. 重複命令為何不會重複執行？
8. 程式中途死亡後如何恢復？
9. 使用者在哪些地方檢查？
10. 哪些仍未接到 live system？

技術正文至少包含：

- architecture diagram
- migration v4
- local tables
- command／projection envelopes
- GAS functions
- dry-run／apply protocol
- receipts
- failure matrix
- exact walkthrough
- tests
- commits
- remaining blockers
- NO-GO boundaries

重要結論標記：

- FACT
- DOCUMENTED INTENT
- INFERENCE
- RECOMMENDATION
- USER ACTION REQUIRED

---

# 十、強制停止條件

遇到任一條，停止該外部 Gate，但繼續完成安全的 local 工作：

- bound Sheet migration 有 blocker
- Sheet 出現非 synthetic data
- repository 不乾淨且來源不明
- 需要碰 live SQLite
- 需要啟停 live Bot
- OAuth scope 超出 staging bridge 所需
- 無法確認 target Spreadsheet
- schema version 不符
- adapter 會讀取人類 views 並覆寫 SQLite
- 需要真實 Discord／Email／Drive 資料
- credential 可能寫入 Git／log／report
- 必須建立公開 endpoint 或 shared secret 才能繼續

不得用人工刪資料、跳過 checksum、改 source version、關閉 guard 或直接 SQL 修正的方式繞過 blocker。

---

# 十一、最終回覆格式

最後只回報：

1. branch／HEAD
2. commits
3. 建立與修改檔案
4. migration v4 結果
5. transport 使用 A／B／C 哪條路徑
6. Local-origin experiment 結果
7. Cloud-origin experiment 結果
8. Idempotency／Rejection experiment 結果
9. tests
10. secrets／live-system side effects
11. 使用者下一個唯一操作
12. blocker
13. git status

不得宣稱：

- live Bot 已 cutover
- live DB 已 migration
- 真實 Discord 已連動
- production scheduler 已啟用
- Email 已接
- Drive archive 已接
- production sync 已完成
