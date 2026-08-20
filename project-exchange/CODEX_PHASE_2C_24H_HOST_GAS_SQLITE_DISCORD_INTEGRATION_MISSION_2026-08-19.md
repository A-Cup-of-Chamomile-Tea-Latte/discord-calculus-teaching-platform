# Codex Mission：Phase 2C — 24h Host、GAS／SQLite／Discord 正式聯動與狀態摘要

> 歷史任務規格，保留作稽核依據，不是 current status。任務起點寫 SQLite v4；canonical
> implementation 現已升至 v5。Busy timeout 的 5 秒規格維持有效。完成度、部署版本與剩餘 gate
> 一律以 `docs/IMPLEMENTATION_STATUS.md` 及本 mission 指定的 report 18 為準。

日期：2026-08-19  
任務性質：**決策已大幅凍結，Codex 主要負責實裝、部署、測試、證據與交接**  
時程原則：開學前加速；只攔截會造成資料遺失、雙重 production writer、credential 外洩、錯誤正式寫入或無法 rollback 的問題。低風險美化與非必要架構純化全部延後。

---

# 0. 本任務的最終目標

把目前已完成的 canonical Discord runtime、SQLite v4、Phase 2B glass-box bridge 與 dual GAS，實際搬到朋友提供的 24 小時 Linux 主機，形成第一版可長期運作的正式拓樸：

```text
                         Google Cloud
                ┌─────────────────────────┐
                │ Bound GAS / Server DB   │
                │ - human views           │
                │ - _CommandInbox         │
                │ - _SyncState            │
                │ - status digest trigger │
                └───────────▲─────────────┘
                            │
                  owner-authenticated
                    Apps Script API
                            │
                ┌───────────┴─────────────┐
                │ Standalone GAS bridge   │
                │ preview/apply/claim/ack │
                └───────────▲─────────────┘
                            │
                            │ outbound only
                            │
┌───────────────────────────┴──────────────────────────────┐
│                   24h Linux Host                        │
│                                                        │
│  course_assistant ─┐                                   │
│                    ├──► Local SQLite ◄── data_bridge   │
│  dump_bot ─────────┘        │                          │
│                              ├── command ledger         │
│                              ├── projection outbox      │
│                              ├── reliable dump jobs     │
│                              └── sync receipts          │
│                                                        │
│  systemd:                                              │
│  - calculus-course-assistant.service                   │
│  - calculus-dump-bot.service                           │
│  - calculus-data-bridge.service                        │
└───────────────────────▲────────────────────────────────┘
                        │
                        │ Discord Gateway / API
                        │
                    Discord Server
```

## 本任務完成後必須成立

1. 24h Linux host 可由 project owner 透過 SSH 安全管理。
2. canonical repository 以可追溯 release 部署到該 host。
3. Discord Bot、SQLite、data bridge 都以 systemd 管理，reboot 後可恢復。
4. Local SQLite 保持 operational authority。
5. Local → Google 使用 durable projection outbox。
6. Google → Local 只經 `_CommandInbox`，不能由 CaseBoard 等人類頁面覆寫 SQLite。
7. Production bridge 使用正式、可刷新、可撤銷的 Google OAuth transport，不依賴 `.clasprc.json`。
8. synthetic real-cloud round-trip 必須先通過。
9. SQLite backup／restore rehearsal 必須先通過。
10. Live cutover 必須顯式停止舊 runtime，禁止新舊 production Bot 同時在線。
11. Cutover 後才啟用 24h background bridge。
12. GAS 每日 07:00、13:30、19:00（Asia/Taipei）寄送簡潔狀態摘要。
13. 狀態摘要即使 24h host 掛掉，仍應由 GAS 根據 stale projection 發出警示。
14. 不在信件、Sheet、Git、report 中暴露學生內容、Discord token、OAuth token 或其他 secret。

---

# 1. 開始前必讀與權威順序

精準閱讀，不要重新掃整個歷史 repository：

1. 最新 canonical `01_CURRENT_DECISIONS*`
2. 最新 canonical `02_SYSTEM_ARCHITECTURE*`
3. 最新 canonical `03_DISCORD_CONFIG*`
4. 最新 canonical `04_GAS_CLASP_PLAN*`
5. 最新 canonical `05_IMPLEMENTATION_STATUS*` / `NEXT_STEPS`
6. `project-exchange/16_PHASE-2A_RUNTIME_QUEUE_DUAL_GAS_REPORT_2026-08-10.md`
7. `project-exchange/17_PHASE_2B_GLASSBOX_DATA_BRIDGE_REPORT_2026-08-11.md`
8. `SHEETS_SCHEMA.md`
9. `docs/PHASE2B_DATA_LAB_GUIDE.md`
10. canonical runtime migrations、queue engine、data_lab、GAS bridge、bound／standalone entrypoints

發生衝突時：

```text
現行 canonical decisions
> 本任務明確凍結的部署決策
> 最新 Phase 2A / 2B evidence
> 舊 branch task / 舊聊天
```

不要用舊文件推翻已經實作並測試的 canonical code。

---

# 2. 已凍結的架構決策

Codex 不得重新辯論以下事項。

## 2.1 Authority

- **Local SQLite**：Discord Bot 的 operational authority。
- **Google Sheets**：current projection、人工管理介面、低頻 command inbox、sync receipts。
- **GAS**：Google 端 UI、validation、preview/apply、command claim/ack、status digest。
- **Git**：程式、schema、migration、policy。
- **受管 archive**：未來完整 dump／附件／manifest；本任務不做完整 Drive archive。
- `CaseBoard`／`Overview`／`Operations`／`History` 永遠不是 Cloud → Local command source。
- `_CommandInbox` 是唯一 Cloud → Local command source。

## 2.2 Discord Bot 不跑在 GAS

Discord Gateway 連線由 24h Linux host 的 canonical runtime 維持。

GAS 不作：

- Discord Gateway host
- 24h socket process
- local SQLite replacement

GAS 只作 cloud control plane。

## 2.3 Remote administration

正式推薦與本任務採用：

```text
Tailscale = private network reachability
OpenSSH + dedicated Ed25519 key = host authentication
```

不要求公開 Internet port 22。

若朋友主機已經有其他安全 VPN／private network，可沿用，但 Codex 不得自行把 SSH 直接暴露到 public Internet。

### 帳號分工

- project owner：一般登入帳號，可 `sudo` 做指定 maintenance。
- `calculus-bot`：system service account，`nologin`，不直接 SSH。
- 不直接使用 root 作日常 SSH 登入。

## 2.4 Linux service manager

正式 host 必須使用 `systemd`。

固定服務：

```text
calculus-course-assistant.service
calculus-dump-bot.service
calculus-data-bridge.service
```

若 host 不是 systemd Linux：

- 完成 read-only audit。
- 停止 production install。
- 回報 blocker。
- 不自行改採 Docker Compose、screen、tmux、cron 或其他永續方式。

## 2.5 Production filesystem

固定 layout：

```text
/opt/calculus-discord/
├── releases/
│   └── <git-sha>/
└── current -> releases/<git-sha>/

/var/lib/calculus-discord/
├── runtime.sqlite3
├── staging/
├── receipts/
├── exports/
└── backups/

/etc/calculus-discord/
├── course-assistant.env
├── dump-bot.env
├── data-bridge.env
└── google-oauth.json
```

規則：

- `/opt/.../releases/<sha>` 不存 mutable runtime data。
- SQLite 不放在 Git tree。
- SQLite 必須位於 host local filesystem，不放 NFS／SMB／雲端同步資料夾。
- credential 全部 `0600`，owner/group 只允許必要 service 讀取。
- logs 優先使用 journald，不建立無限制成長的自訂 log。
- `current` symlink 用於 release cutover／rollback。

## 2.6 SQLite concurrency

24h host 上 course_assistant、dump_bot、data_bridge 共用同一 SQLite。

沿用現有短 transaction、claim／lease 設計。

Codex 必須檢查 canonical DB helper：

- 若已設定 WAL／busy timeout，保留並測試。
- 若沒有，為 local-file production profile 增加：
  - WAL mode
  - reasonable busy timeout（預設 5 秒）
  - foreign key pragma 若 schema 已依賴 FK
- 不因本任務重寫 repository abstraction。
- 不讓外部 Google API call 包在長時間 SQLite transaction 裡。

## 2.7 Production background cadence

正式預設：

| 工作 | 預設 |
|---|---:|
| Discord event → SQLite | 立即 |
| Projection flush | 每 60 秒 |
| Projection threshold | 20 pending work 可提前 flush |
| Projection batch maximum | 50 |
| Cloud command poll | 每 60 秒 |
| local health receipt | 每 60 秒 |
| `Operations` cloud publish | 每 5 分鐘或狀態改變 |
| stale | 15 分鐘 |
| critical stale | 30 分鐘 |
| projection worker | 1 |
| command consumer | 1 |

規則：

- Discord handler 不等待 Google。
- Google API failure 只留下 durable local work。
- current-state projection 可以 coalesce。
- History lifecycle event 不 coalesce，但必須以穩定 event ID 去重。
- 不每則 Discord message 呼叫 Google。

---

# 3. 使用者、朋友、Codex 分工

## 3.1 使用者只需要做

A. 遠端主機：

1. 產生／選擇 SSH public key。
2. 把 **public key** 給朋友。
3. 取得：
   - SSH username
   - Tailscale hostname 或 private IP
4. 第一次登入時人工確認 host key fingerprint。
5. 若 Google OAuth flow 需要瀏覽器，只完成一次帳號授權。
6. Live cutover 前回覆唯一明確字串：
   - `GO-LIVE-CUTOVER`

B. Google：

- 若 compact Sheet migration 尚缺 receipt，依既有流程做：
  - dry-run
  - apply
  - second dry-run no-op
- 若 Codex 需要 standard Cloud project／OAuth consent 的人工 UI 步驟，只做 Codex 明確列出的最少步驟。

## 3.2 朋友只需要做

- 在 host 建 project owner 的 SSH login。
- 把使用者 public key 加入 `authorized_keys`。
- 提供 Tailscale/private hostname。
- 如 project owner 需要 sudo，授予必要 sudo。
- 不需要碰 Discord/GAS/SQLite application 設計。

## 3.3 Codex 負責

除了上述人工 gate，其餘：

- host audit
- repository packaging/deployment
- system user/path/permissions
- virtualenv/runtime dependencies
- systemd units
- staging SQLite
- Google OAuth transport
- GAS API executable setup code／runbook
- synthetic real-cloud smoke
- backup/restore drill
- production cutover rehearsal
- live cutover（只在 GO 後）
- post-cutover smoke
- background bridge
- GAS status digest
- tests
- rollback
- docs/report

不要把低層實作問題丟回使用者。

---

# 4. Gate A — Repository 與 local baseline

開始前：

1. 找 canonical root。
2. `git status --short` 必須乾淨；若來源不明地不乾淨，停止 mutation。
3. 記錄：
   - current branch
   - HEAD
   - latest Phase 2B commits
   - Python／Node／SQLite／clasp versions
4. 確認 Phase 2B 至少存在：
   - SQLite v4
   - `case_lifecycle_events`
   - `inbound_commands`
   - `projection_outbox`
   - `sync_state`
   - data lab CLI
   - bridge CLI
   - GAS bridge functions
5. 跑一次 **targeted baseline only**：
   - runtime migration/bridge tests
   - GAS bridge tests/typecheck/build
6. 不跑 Portal、NAP、完整 repository suite。

若目前 branch 與最新 Phase 2B 交接不一致：

- 先找清楚 canonical commit。
- 不盲目 cherry-pick 舊 branch。
- 不建立第二套平行 implementation。

---

# 5. Gate B — Remote SSH 與 host audit

在使用者提供 SSH target 後：

## 5.1 第一次連線

- 使用 OpenSSH key auth。
- 嚴格 host key checking。
- 不用 password automation。
- 不把 private key 複製到 repository。
- 不把 private key 傳到 remote host。

## 5.2 唯讀 audit

取得：

- distro / version
- kernel
- architecture
- systemd version
- Python
- Node
- SQLite CLI/library
- disk free
- memory
- CPU
- timezone
- NTP sync
- Tailscale/private connectivity
- existing users/services relevant to this project
- whether ports must be opened

禁止在 audit 階段：

- firewall change
- Docker install
- global dependency upgrade
- reboot
- SSH daemon config rewrite

### Pass requirement

必須：

- systemd Linux
- host local writable filesystem
- Asia/Taipei 可配置
- NTP 正常
- 足夠 disk space
- project owner 有必要 sudo
- outbound HTTPS 可用
- Discord outbound connectivity 可用（不登入 bot）
- Google API outbound connectivity 可用

若硬體資源明顯足夠即可，不做無意義 benchmark。

---

# 6. Gate C — 建立 production host skeleton

在 remote host 建：

## 6.1 service account

```text
calculus-bot
```

- system account
- no interactive shell
- dedicated group
- no sudo

## 6.2 directories

建立 frozen layout，權限最小化。

建議：

- `/opt/calculus-discord` root-owned
- release code readable by service
- `/var/lib/calculus-discord` calculus-bot writable
- `/etc/calculus-discord` root-owned
- secret files group-readable only if service 需要

## 6.3 repository release

優先順序：

A. 若 canonical repo 有可安全使用的 private Git remote：
- clone/fetch exact commit。
- 不 checkout floating branch 作 production source。

B. 若沒有可用 remote：
- 從 local clean Git 建 `git bundle` 或等效可驗證 artifact。
- 傳到 remote。
- checkout exact commit。

禁止：

- rsync 整個 dirty working tree
- 搬 `.gitignore` 內 secret/data
- 手工挑 Python 檔拼 production tree

保存：

```text
release git SHA
deployment timestamp
artifact SHA-256（若有）
```

## 6.4 Python environment

- 依 canonical lock/packaging 安裝。
- 使用 project-local or release-specific venv。
- 不 global pip install application dependencies。
- 不任意升級 dependency。

---

# 7. Gate D — Remote staging runtime，不連 production Discord

先在 remote host 建 staging profile：

```text
environment=STAGING
synthetic_only=1
live_discord_enabled=0
```

建立獨立：

```text
/var/lib/calculus-discord/staging/staging.sqlite3
```

執行：

1. migration empty → v4
2. synthetic local-origin ingest
3. projection outbox
4. inspector
5. restart/reopen DB
6. queue claim/lease recovery

不得：

- 複製 live SQLite
- 啟動 Discord Gateway
- 使用 Discord token
- 使用 production env file

---

# 8. Gate E — Production Google transport

目前 Phase 2B 真實 cloud smoke 的 blocker 是 local host 尚無正式 authenticated transport。

本任務固定採：

```text
Local data_bridge
→ Google Apps Script API scripts.run
→ standalone GAS API executable
→ bound Server Database
```

## 8.1 禁止的 transport

不得：

- 解析 `.clasprc.json` 當 runtime credential
- 使用 service account 呼叫 Apps Script API
- public anonymous web app
- shared-secret public endpoint
- 把 OAuth token 寫入 Git
- 直接把 CaseBoard 作 input

## 8.2 Standard Google Cloud project

Codex 檢查 standalone GAS 是否已綁 standard Google Cloud project。

若沒有：

1. 準備最小變更 runbook。
2. 讓使用者只完成必要 Google Console UI。
3. standalone script 與 local OAuth client 必須共用該 Cloud project。
4. 啟用 Apps Script API。
5. 建 OAuth client 給 local bridge。

不要為此建立第二個不受控 GAS source tree。

## 8.3 API executable

Standalone GAS 建立 immutable staging API executable deployment。

只暴露既有或對應 wrapper：

```text
bridgePreview
bridgeApply
bridgeClaimCommand
bridgeAckCommand
bridgeHealth
```

函式只收／回 basic JSON-compatible values。

## 8.4 OAuth scope minimization

Standalone API executable 與 bound status-mail script 的責任保持分離。

Production local bridge OAuth token只需 standalone bridge 真正需要的 scope。

不要因狀態摘要寄信，把 `send_mail` scope 無必要地塞給 local bridge OAuth。

若 standalone project 內已有其他功能導致 OAuth scope 過廣：

- 優先拆 entrypoint/manifest responsibility，不重寫 domain code。
- 報告 exact scopes。
- 任何新增 sensitive scope 必須標成 USER ACTION REQUIRED。

## 8.5 Credential carrier

Local OAuth 完成後：

```text
/etc/calculus-discord/google-oauth.json
```

- 不存 client secret/token 到 Git。
- report 不輸出 token。
- chmod 0600。
- service account 只讀。
- refresh token 可撤銷。
- 不使用 `.clasprc.json`。

若 OAuth 必須在有瀏覽器的 local Mac 完成：

- 使用專門 bootstrap helper 取得 credential。
- secure-copy credential 到 remote。
- local temporary token artifact 完成後依 runbook清理或保護。
- 不要求使用者把 token 貼到聊天。

---

# 9. Gate F — Bound Sheet compact migration

若尚未有完整三段 receipt：

1. dry-run
2. apply
3. second dry-run = no-op

Codex 只準備檢查與收據，不自行人工刪舊 Sheet。

遇 blocker：

- 停止 cloud mutation。
- 保留 remote staging成果。
- 回報具體 tab/key blocker。

只有 schema 2.0.0、target fingerprint、synthetic-only gate 都正確，才進下一步。

---

# 10. Gate G — Remote host ↔ Real Google synthetic smoke

在 **remote 24h host** 上完成，而不是只在使用者 Mac。

## 10.1 Local → Cloud

1. remote staging DB 建 `TST-` case。
2. project dry-run。
3. 驗證 Google preview：
   - target fingerprint
   - schema
   - checksum
   - source version
   - zero mutation
4. apply。
5. 驗證：
   - CaseBoard synthetic row
   - Overview synthetic count
   - Operations staging status
   - History OPEN 只有一筆
   - `_SyncState` receipt
   - local outbox completed
6. 同 envelope 重送：
   - no-op
   - History 不重複 append

## 10.2 Cloud → Local → Cloud

1. bound data lab 提交一筆 CLOSE synthetic command。
2. remote bridge claim。
3. dry-run 時 staging DB hash 不變。
4. apply。
5. local case CLOSED。
6. projection 回 Google。
7. 驗證：
   - `_CommandInbox` receipt
   - CaseBoard CLOSED
   - History CLOSE 只有一筆
   - local inbound ledger APPLIED
8. duplicate command：
   - no duplicate lifecycle event
   - no duplicate side effect

Pass 後才能稱：

> remote-host real-cloud synthetic round-trip verified

仍不得稱 production Discord 已聯動。

---

# 11. Gate H — Production data_bridge daemon

Synthetic cloud smoke 通過後，建立：

```text
calculus-data-bridge.service
```

## 11.1 行為

同一 process 內可有兩個 lightweight loops：

A. projection loop  
B. command polling loop

但 concurrency：

```text
projection worker max = 1
command consumer max = 1
```

不需要額外 message broker。

## 11.2 Timing

- 起動後先 health check。
- command poll every 60s ± small local jitter。
- projection flush every 60s。
- pending >= 20 可立即 flush。
- batch <= 50。
- Operations publish every 5 min or state change。
- graceful shutdown 在 systemd SIGTERM 時停止新 claim，完成／釋放目前 lease。

## 11.3 Failure

Google unavailable：

- Bot 不停。
- SQLite work 保留。
- bounded retry/backoff。
- Operations 在可恢復後更新。
- 不 spam log。

OAuth expired/revoked：

- data bridge 進 degraded。
- Discord Bot 繼續。
- 不刪 queue。
- status digest 應能顯示 projection stale。

## 11.4 systemd

Unit 必須至少：

- `User=calculus-bot`
- `Group=calculus-bot`
- exact release/current path
- `EnvironmentFile=`
- `Restart=on-failure`
- bounded restart delay
- working directory
- no root execution
- graceful stop timeout

使用合理 hardening，但不要因追求完美 systemd sandbox 造成 Discord/GAS network 被封鎖。

---

# 12. Gate I — Backup／restore rehearsal

Live cutover 前必須做。

使用 remote synthetic v4 DB：

1. 寫 synthetic case。
2. 留一筆 pending job。
3. 留一筆 expired claimed job。
4. 使用 SQLite consistent backup mechanism 產生 backup。
5. SHA-256。
6. 還原到不同 path。
7. `PRAGMA integrity_check`。
8. inspector compare：
   - schema version
   - tables
   - row counts
9. fixture worker reclaim expired job。
10. 原 DB 與 restored DB 相互獨立。
11. 刪 disposable rehearsal data。

保存：

- command
- result
- checksum prefix
- restore pass/fail

不在報告輸出 application row content。

---

# 13. Gate J — Live cutover rehearsal

正式 cutover 前，Codex 必須先輸出 machine-checkable runbook 並做 dry-run。

## 13.1 Current old runtime audit

唯讀確認：

- 舊 `.local` runtime launch mechanism
- course_assistant process
- dump_bot process
- live SQLite path
- current env file locations
- current Bot token variable names
- current provisioning mapping location

不要在報告輸出 secret value 或 Discord IDs。

## 13.2 Secret migration plan

正式 cutover 需要現有 Bot credential。

允許 Codex在 **GO-LIVE-CUTOVER 後** 做 one-time secure transfer，但：

- 不 print
- 不 cat 到 terminal transcript
- 不存 Git
- 不存 report
- 使用 secure file copy／install
- remote file chmod 0600
- 完成後 secret scan 不得找到值

若無法安全轉移，停止並要求使用者人工建立 remote env file；不要要求貼 token 到聊天。

## 13.3 Live DB migration rehearsal

在舊 host：

1. 先以 SQLite consistent backup 建 live DB 副本。
2. 不在原 live DB 直接試 migration。
3. 在 disposable copy：
   - migrate → current
   - integrity_check
   - inspector
   - canonical runtime repository tests/read-only startup
4. rehearsal pass 才能進正式 cutover。

---

# 14. USER GATE — `GO-LIVE-CUTOVER`

到這裡停止。

向使用者回報一個非常短的 readiness summary：

```text
SSH/host        PASS
remote staging  PASS
Google bridge   PASS
cloud smoke     PASS
backup restore  PASS
DB rehearsal    PASS
rollback        READY

唯一下一步：GO-LIVE-CUTOVER
```

使用者沒有回覆精確 `GO-LIVE-CUTOVER` 前：

- 不停舊 Bot
- 不搬 live DB
- 不啟動 remote production Bot
- 不改 production credentials

---

# 15. Gate K — 正式 Live Cutover

收到 `GO-LIVE-CUTOVER` 後一次完成，不分散數天。

## 15.1 Freeze

1. 記錄開始時間。
2. 停止舊 host 的 Bot writers：
   - course_assistant
   - dump_bot
   - 任何會寫 live SQLite 的 bridge/sweep
3. 驗證 process 確實退出。
4. 等待短暫 grace period。
5. **禁止先啟動 remote Bot「看看」。**

## 15.2 Backup

1. 產生一致性 live SQLite backup。
2. SHA-256。
3. 保存 owner-only rollback copy。
4. 不修改 rollback copy。

## 15.3 Transfer

1. secure copy DB 到 remote temporary path。
2. secure copy必要 production config/secrets。
3. checksum compare。
4. chmod/chown。

## 15.4 Migration

remote：

1. 在 transferred DB copy migration。
2. integrity_check。
3. migration ledger verify。
4. inspector。
5. atomic move 成：
   `/var/lib/calculus-discord/runtime.sqlite3`

## 15.5 Start order

固定：

```text
1. course_assistant
2. health verification
3. dump_bot
4. health verification
5. data_bridge
```

每一步失敗就停後續。

## 15.6 Single-active-writer invariant

Cutover 成功前後必須證明：

- 舊 host Bot process = 0
- remote production Bot process = exactly expected
- 舊 LaunchAgent/system mechanism 已 disabled，不會 reboot 後自己復活
- remote systemd enabled
- 只有 remote host 使用 production DB

若無法證明，停止。

## 15.7 Discord smoke

只做最小 allowlisted test：

- Bot login
- health
- 一筆不破壞資料的 Public test case 或既有官方 smoke
- Private 只做既有安全 smoke，不建立敏感真人資料
- 不做大型壓測

## 15.8 Rollback trigger

遇：

- migration inconsistency
- Bot 無法登入
- repeated Discord action
- DB corruption
- critical queue failure
- production secret missing
- unexpected duplicate process

立即：

1. stop remote services
2. 不讓新舊同時啟動
3. restore/retain rollback DB
4. 修復後再決定舊 host是否重新啟用
5. 若回舊 host，remote 必須保持 stopped

---

# 16. Gate L — Post-cutover 24h service

Pass 後：

- enable 三個 systemd services
- reboot persistence test（可安排 maintenance window；若立即 reboot 風險過高，可至少做 service restart test，並把 full reboot 列為下一 maintenance）
- verify SQLite path
- verify journald
- verify data bridge backlog drains
- verify Google Operations current
- verify stale alert logic

不要在 production 第一天新增其他 feature。

---

# 17. GAS 狀態摘要信

這個功能是 **cloud-side watchdog**，不是 local host 自己寄信。

如果 24h host 掛掉，GAS 仍可根據 Google Sheet 最後一次 Operations／Sync receipt 判定 stale 並寄出警示。

## 17.1 固定寄送時段

Asia/Taipei：

```text
07:00
13:30
19:00
```

Apps Script time trigger 有時間漂移，因此固定使用：

```text
everyMinutes(5) dispatcher
```

dispatcher 自己判斷現在是否已進入尚未處理的 slot。

不建立三個假裝精準的 daily hour trigger。

## 17.2 Slot

固定 slot key：

```text
YYYY-MM-DD:0700
YYYY-MM-DD:1330
YYYY-MM-DD:1900
```

每個 slot 最多嘗試一次正常 send。

狀態保存於：

```text
PropertiesService.getScriptProperties()
```

不要使用 deprecated `ScriptProperties` class。

## 17.3 Recipient

放 Script Properties，例如：

```text
STATUS_EMAIL_RECIPIENTS
```

不放：

- Sheet cell
- Git
- source code
- report

第一版只寄 project owner；多收件人未來再加。

## 17.4 Mail content：刻意簡潔

禁止眼花撩亂 dashboard dump。

Subject：

```text
[微積分 Bot] 正常｜07:00
[微積分 Bot] 注意｜13:30
[微積分 Bot] 異常｜19:00
```

Body 固定最多四區：

```text
整體狀態：正常 / 注意 / 異常

需要你處理：
無
或
- Bot 已超過預期時間沒有回報，請登入主機檢查。

最近狀況：
- Discord Bot 正常 / 有異常
- 資料同步正常 / 延遲
- 案件目前無需特別處理 / 有待處理案件

資料時間：
最後更新 HH:MM
```

只有異常時才補：

```text
安全錯誤代碼：<SAFE_CODE>
```

不要列：

- PID
- memory
- CPU
- queue 每種數字
- stack trace
- raw error
- Discord ID
- 學生資料
- message body

若有少量 TA 待處理案件，可以寫：

```text
目前有待處理案件。
```

除非數量對行動有實際意義，否則不列數字。

## 17.5 Status classification

NORMAL：

- course_assistant recent
- dump_bot recent
- bridge projection recent
- 無 terminal failure 需要人工處理

ATTENTION：

- projection stale > 15 min
- retryable failure 持續
- 有待人工處理但系統仍可服務

CRITICAL：

- Bot／projection stale > 30 min
- permanent failure
- OAuth revoked
- production service explicitly reports DOWN

若 Google 本身無法取得新 local projection：

- 使用 last receipt age 判定。
- 不假裝 host normal。

## 17.6 At-most-once preference

狀態摘要是 best-effort watchdog，不是交易型 Email。

為避免同一 slot 重複狂寄：

1. 取得 ScriptLock。
2. 檢查 slot。
3. 寫入 `ATTEMPTING` receipt。
4. 呼叫 `MailApp.sendEmail`。
5. 成功後標 `PROVIDER_ACCEPTED`。
6. 若 execution 在 send 後、receipt 前死亡：
   - 下一 dispatcher 不自動重寄該 slot。
   - 標記 ambiguous/attempted。
   - 下一正常 slot 再寄。

寧可漏一封摘要，不要 duplicate spam。

## 17.7 Test

使用 fixture Operations／SyncState：

- normal
- stale
- critical
- no-data
- same-slot rerun
- lock contention
- MailApp error before send
- ambiguous receipt state

正式啟用前只寄 project owner 測試地址。

---

# 18. 不在本任務做的東西

為了開學前速度，以下延後：

- Drive 完整 archive adapter
- attachment upload
- Public weekly batch dump
- Members 完整 production projection
- Email verification 全流程
- production 任意 CommandInbox 操作擴張
- HMAC/signature 升級
- LLM analysis
- Portal 美化
- dashboard 數據擴充
- 第三隻 bot
- 監控平台 Prometheus/Grafana
- Kubernetes
- Docker 化純化
- HA SQLite replication

除非某項是本任務 blocker，不得順手做。

---

# 19. Critical reliability tests

只測開學前真的重要的：

## Remote host

- service crash → systemd restart
- service stop → clean SQLite state
- data bridge Google timeout → Bot 不中斷
- OAuth revoked → bridge degraded，Discord still alive
- SQLite locked briefly → bounded retry
- duplicate worker protection
- host process listing confirms single production Bot instance

## Bridge

- duplicate command same idempotency → no-op
- duplicate projection same version/checksum → no-op
- History stable event ID prevents duplicate append
- partial Google write without `_SyncState` success → local outbox remains
- same version/different checksum → reject
- stale version → reject
- wrong target fingerprint → reject

## Cutover

- migration rehearsal
- checksum transfer
- rollback path
- old host writer stopped before new host start

## Digest

- host fresh → NORMAL
- 15+ min stale → ATTENTION
- 30+ min stale → CRITICAL
- slot duplicate → no second email

---

# 20. Quota／時間策略

這是一個大任務，但不要浪費 Codex quota。

每個 Gate：

- 精準讀 relevant files。
- 跑 targeted tests。
- 不每改一行都 full suite。
- 不重建 Portal。
- 不重跑 NAP。
- 不做 style refactor。

Final integration gate 才跑：

- canonical runtime relevant suite
- migration／queue／bridge tests
- GAS tests/typecheck/build
- systemd syntax/verify
- secret scan
- `git diff --check`

Remote host deployment evidence 以 command result、service state、safe fingerprints 為主。

---

# 21. Git 策略

不把 remote host 當開發機。

開發仍在 canonical local repository。

建議最多：

1. `feat(bridge): add production apps-script-api transport`
2. `feat(runtime): add production bridge service profile`
3. `ops(host): add systemd deployment and cutover tooling`
4. `feat(gas): add concise status digest watchdog`
5. `test(ops): cover production integration failure paths`
6. `docs: add 24h host runbook and phase2c handoff`

Remote `/opt/.../releases/<sha>` 必須對應 clean Git commit。

不要把 remote-only hotfix 留在主機。

---

# 22. 文件交付

新增：

```text
docs/ops/24H_HOST_DEPLOYMENT.md
docs/ops/LIVE_CUTOVER_RUNBOOK.md
docs/ops/GOOGLE_BRIDGE_OAUTH.md
docs/ops/STATUS_DIGEST.md
```

建立唯一主要交接報告：

```text
project-exchange/18_PHASE_2C_24H_HOST_PRODUCTION_INTEGRATION_REPORT_2026-08-19.md
```

報告開頭必須有：

# 十分鐘白話版

回答：

1. Discord Bot 現在實際跑在哪裡？
2. SQLite 在哪裡，誰是 authority？
3. GAS 與 local server 怎麼互相聯絡？
4. Google 掛掉時 Discord 還能不能服務？
5. local server 掛掉時為什麼 GAS 還能寄警示？
6. 怎麼確定沒有兩套 production Bot 同時跑？
7. 怎麼 backup／restore？
8. 怎麼遠端登入？
9. 哪些 secret 在哪裡，但不得列值？
10. 現在距離開學可用還缺什麼？

---

# 23. 強制停止條件

遇到以下任一條，停止相關 mutation：

- repository dirty 且來源不明
- remote host 不是 systemd Linux
- 需要把 SSH 暴露 public Internet 才能繼續
- 無法確認 host key
- Google OAuth scope 明顯超出 bridge 必需
- 只能靠 service account 呼叫 Apps Script API
- 只能靠 public web endpoint/shared secret
- bound Sheet migration 有 blocker
- production Sheet 出現未知非預期資料
- live DB rehearsal migration 失敗
- backup restore 失敗
- 無法安全停止舊 runtime
- 無法證明舊 production writer 已退出
- credential 可能被 echo/log/report
- remote DB checksum transfer 不一致
- Discord 出現重複副作用
- rollback path 不可用

不要為趕時間跳過：

- backup
- old writer stop verification
- migration rehearsal
- secret isolation
- real cloud synthetic smoke

其餘低風險細節可以直接採合理預設繼續。

---

# 24. 最終回報格式

每個主要 milestone 完成後不要寫長篇聊天。

最終只回：

1. local branch／HEAD
2. remote release SHA
3. SSH/Tailscale：PASS／BLOCKED
4. remote staging：PASS／BLOCKED
5. Google OAuth transport：PASS／BLOCKED
6. real-cloud synthetic round-trip：PASS／BLOCKED
7. backup/restore：PASS／BLOCKED
8. live cutover：NOT STARTED／PASS／ROLLED BACK
9. course_assistant：狀態
10. dump_bot：狀態
11. data_bridge：狀態
12. GAS status digest：TESTED／ENABLED／BLOCKED
13. secrets findings：0 或 blocker
14. 使用者下一個唯一操作
15. git status

若到 USER GATE，唯一操作必須是：

```text
GO-LIVE-CUTOVER
```

不要同時丟五個決策題給使用者。
