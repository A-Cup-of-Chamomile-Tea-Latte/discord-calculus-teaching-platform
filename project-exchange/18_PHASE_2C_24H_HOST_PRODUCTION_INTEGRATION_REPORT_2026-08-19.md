# Phase 2C：24h Host、GAS／SQLite／Discord 正式聯動報告

> Canonical snapshot：2026-08-20 Asia/Taipei
>
> Branch：`codex/phase-2c-24h-production-integration`
>
> 已部署與驗證的 code baseline：`78fb4a8`
>
> 歷史收據：本文件保存 cutover 前狀態，不再作為 current source of truth。Phase 2C v6 baseline 已在
> 2026-08-24 17:16 完成 24 小時 observation 並判定 PASS；現況請看
> `docs/ops/PHASE2C_24H_OBSERVATION.md`、`docs/IMPLEMENTATION_STATUS.md` 與 `docs/NEXT_STEPS.md`。

## 結論

本機能完成的 Phase 2C 前置工作已完成。兩隻 Discord Bot 仍由 Mac 單一實例運作，沒有
live cutover。SQLite 仍是唯一資料權威；Google Sheets 維持 5 個人用頁與 5 個隱藏機器頁，
不是第二套主資料庫。

已實測完成雙向 Bridge：Local → Cloud projection，以及 Cloud → Local → Cloud command 的
queue、claim、apply、ack 與 duplicate-safe replay。Synthetic human-view rows 已安全清除，最後
dry-run 為 no-op。Live SQLite 只以唯讀方式開啟；consistent backup、restore、copy migration
v0 → v5、integrity、ledger 與 row-count equivalence 全部通過，原始 DB 未修改。

以下結論與 gate 表是 2026-08-20 的歷史切面；其中 remote host、cutover、OAuth 與 24 小時觀察等
舊 gate 均已由後續 canonical 文件汰換。

## Historical canonical runtime（2026-08-20）

| 項目 | 現況 |
| --- | --- |
| `course_assistant` | Mac RUNNING；1 instance |
| `dump_bot` | Mac RUNNING；1 instance |
| Production writer | 只有 Mac；remote 尚無 writer |
| Tracked SQLite | migration v5 |
| Live Mac SQLite | legacy v0；未修改；copy rehearsal PASS |
| Standalone GAS | immutable v12；owner-only Execution API；無 public Web App |
| Bound GAS | immutable v6；source aligned；trigger 未啟用 |
| Compact Sheet | schema `2.0.0`；5 visible + 5 hidden |
| Remote host | BLOCKED；尚缺 host identity |

## 雙向 cloud smoke 收據

### Local → Cloud projection

1. Preview：4 筆 pending；沒有 cloud mutation。
2. Apply：4 筆 completed。
3. Replay：`NO_WORK`／queue empty。
4. Cleanup：5 筆 human-view synthetic rows 移除。
5. Final dry-run：removable 0、unknown 0、blockers 0。

### Cloud → Local → Cloud command

1. Owner-only synthetic command enqueue：QUEUED。
2. Fetch preview：PREVIEW。
3. Fetch apply：COMMAND_APPLIED；本機只新增一筆 synthetic case／command ledger。
4. Duplicate fetch：NO_WORK。
5. Projection apply：4 筆 completed；duplicate projection：NO_WORK。
6. Remote pending commands：0。
7. Cleanup：human-view synthetic rows 移除；保留一筆 terminal machine receipt，作短期稽核與
   version watermark。

Cleanup 只接受嚴格識別的 STAGING synthetic rows；遇 blank／duplicate primary key、formula、
nonce 變動或 unknown row 即 fail closed。`_CommandInbox`、`_EmailOutbox`、`_Artifacts` 不由
cleanup 刪除；`_SyncState` watermark 保留。由於 Sheet 沒有跨人工編輯的原子 transaction，
實際 cleanup 只能在禁止人工同時編輯的短窗口執行；本輪即依此完成。

## SQLite recovery 收據

| 檢查 | 結果 |
| --- | --- |
| Source 開啟模式 | read-only |
| Source during rehearsal | 檔案穩定、未修改 |
| Consistent backup／restore | PASS |
| `integrity_check` | PASS |
| Copy migration | v0 → v5；5 筆 migration ledger |
| Schema counts | source 5 tables → migrated copy 11 tables |
| Row-count equivalence | PASS |
| Restored-copy independence | PASS |
| Temporary rehearsal artifacts | 已移除 |

新增可執行 `sqlite-restore.sh` 與 `sqlite-recovery-rehearsal.py`；因此 backup 與 restore rehearsal
tooling 現在都在 repository。Remote rehearsal 仍必須在取得 host 後另跑，不能用本機 copy
receipt 代替。

## 自動驗證

| Suite | 結果 |
| --- | --- |
| Python | 246 passed；2 upstream deprecation warnings |
| Portal | 53 passed |
| Config Studio | 3 passed |
| GAS | 66 passed |
| GAS typecheck／standalone＋bound build | PASS |
| GAS pull-back fingerprint | PASS |
| Mac Bot single-instance | PASS |
| Secret／credential boundary | `.local/` ignored；未加入 repo／報告 |

## Google OAuth 的誠實限制

本機 credential 可刷新且 `scripts.run` 已通過，但 Google Auth Platform 仍是 External／Testing，
scope 包含 Sheets。依 Google 規則，這類 testing refresh token 通常約 7 天失效，不能稱為
長期 credential。

24h production 前，owner 必須二選一：

1. 將 publishing status 切到 Production，處理 Google 要求的驗證，再於 Chrome「Ding Ding」
   重新授權一次；或
2. 接受 Testing 模式，並把約每 7 天重新授權納入維運。

此選擇不會把 GAS 變成公開 endpoint；standalone deployment 仍維持 owner-only。

## 剩餘工作只分兩類

### A. 需要人工網頁／外部資訊／明示授權

1. 決定 Google OAuth Production 或週期性 reauthorization。
2. 朋友提供 SSH username、Tailscale hostname／private IP；首次連線由使用者人工核對 host-key
   fingerprint。
3. Codex 完成 remote read-only audit、staging、remote cloud smoke、backup／restore 與 one-writer
   readiness 後，使用者才可輸入精確 `GO-LIVE-CUTOVER`。
4. Remote heartbeat 穩定後，必要時人工授權 bound GAS status-digest trigger。

### B. 必須等待實際時間

- Cutover 後才開始 24 小時 observation；驗證單一 writer、三個 remote services、Discord、queue、
  OAuth refresh、GAS heartbeat、backup 與 Sheet projection。不能用加速測試代替。

## Historical gate 表（2026-08-20）

| Gate | 狀態 |
| --- | --- |
| Local implementation／tests | PASS |
| Compact Sheet／safe cleanup | PASS |
| Local bidirectional real-cloud synthetic smoke | PASS |
| Live-copy backup／restore／migration rehearsal | PASS |
| Google OAuth longevity decision | MANUAL GATE |
| SSH／Tailscale identity | BLOCKED ON EXTERNAL INPUT |
| Remote staging／remote cloud smoke | WAITING FOR HOST IDENTITY |
| Remote backup／restore | WAITING FOR HOST IDENTITY |
| `GO-LIVE-CUTOVER` | NOT AUTHORIZED |
| 24h observation | NOT STARTED（當時；已由 2026-08-24 PASS 收據汰換） |
| Bound status digest | TESTED／NOT ENABLED |

## 固定停止線

- 未收到精確 `GO-LIVE-CUTOVER`：不停 Mac bots、不搬 live DB、不啟動 remote production writer。
- 不把 raw messages、姓名、學號、Discord ID、Email、附件、Private Support、credential、SQLite
  row content 放入聊天、Git、公開 ZIP 或 LLM。
- Corpus／LLM 分析、public endpoint、email 正式寄送與學生試用不在本次授權範圍。
