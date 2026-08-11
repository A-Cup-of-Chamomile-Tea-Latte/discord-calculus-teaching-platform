# Phase 2B 資料聯動實驗室

這是一個人工觸發、只用假資料的 staging 實驗室。它不會連線 Discord、不會打開 live
SQLite、不會寄信，也沒有排程器。每次都先看 dry-run，再用同一個 nonce 確認 apply。

## 三個位置

| 位置 | 用途 | 權威來源 |
|---|---|---|
| `.local/phase2b-data-lab/staging.sqlite3` | 假案件狀態、命令帳本、投影佇列 | 是 |
| Google Sheet | 給人看的精簡投影；只有 `_CommandInbox` 可輸入 | 否 |
| `docs/` 與 Git | 規則、程式、手冊與可審查歷史 | 否 |

`CaseBoard` 不是輸入管道。人工直接改它，本機 fetcher 也不會讀它來覆寫 SQLite。

## 實驗 A：本機建立假案件

在 canonical project root 執行：

```bash
cd runtime/discord-course-bots
.venv/bin/python -m discord_course_bots.data_lab.cli_lab \
  ingest --fixture fixture://public/basic-v1 --dry-run
```

輸出會顯示 `STAGING`、`syntheticOnly: true`、`databaseUnchanged: true`、預計狀態變化、四個
outbox scopes 與 `confirmationNonce`。把剛才的 nonce 放入 apply：

```bash
.venv/bin/python -m discord_course_bots.data_lab.cli_lab \
  ingest --fixture fixture://public/basic-v1 --apply --confirm <nonce>
```

查看案件與整體狀態：

```bash
.venv/bin/python -m discord_course_bots.data_lab.cli_lab \
  case-status --case-ref TST-BASIC-001
.venv/bin/python -m discord_course_bots.data_lab.cli_lab summary
```

若要自己填 module、keyword、TA action 與假 deadline：

```bash
.venv/bin/python -m discord_course_bots.data_lab.cli_lab create-case --interactive
```

Wizard 會先印出計畫與 nonce；沒有輸入同一 nonce 就不會寫入。

## 實驗 B：先看投影差異

```bash
.venv/bin/python -m discord_course_bots.data_lab.cli_bridge \
  project --once --dry-run
```

目前命令使用 fake transport：dry-run 不改 SQLite，也不改 Cloud。它會將 canonical envelope
存在已被 Git ignore 的 `projection-bundles/`，讓 apply 使用「同一 envelope＋同一 nonce」。

```bash
.venv/bin/python -m discord_course_bots.data_lab.cli_bridge \
  project --once --apply --confirm <nonce>
```

在 transport C 模式下，這個 apply 只對 fake GAS 執行整合測試，不會呼叫真實 Sheet。

## 實驗 C：Sheet 假命令

只有完成 compact migration 三段 receipt 後，才可開啟：

```text
微積分模組管理 → 資料聯動實驗室
```

Sidebar 只有六個固定動作，沒有任意 JSON 輸入框。它寫入 `_CommandInbox`，再由本機
one-shot fetch 先預覽：

```bash
.venv/bin/python -m discord_course_bots.data_lab.cli_bridge \
  fetch --once --dry-run
```

真實 remote transport 尚未開啟，所以 CLI 會回報無工作；兩端的 claim、lease、stale-token 與
idempotency 已由 fake integration tests 驗證。

## 保護機制

| 機制 | 防止的問題 |
|---|---|
| source fingerprint | 寫到錯的 Spreadsheet |
| schema version | 兩邊對欄位的理解不同 |
| source version | 舊命令倒灌、投影回滾 |
| checksum | 傳輸後內容被改動或不完整 |
| confirmation nonce | 操作者看 A 卻套用 B |
| idempotency key | 斷線重試時重複改變案件 |
| claim token + lease | 兩個 worker 同時執行，或死掉的 worker 永久佔住工作 |

## 中斷後怎麼恢復

- dry-run 中斷：重跑即可，SQLite 沒有變更。
- local commit 前中斷：transaction rollback，下次可安全重試。
- local commit 後、remote ack 前中斷：帳本辨識同一 command ID，回傳 no-op，不再改案件。
- GAS 寫人類視圖後中斷：沒有 `_SyncState` success receipt，本機 outbox 不會標記
  `COMPLETED`；下次透過 version/checksum 安全重試。

## 停止線

- 不得指向 live SQLite。
- 不得開啟 Discord gateway、daemon、trigger 或 public web endpoint。
- 不得使用姓名、學號、Discord ID、Email、訊息內文、附件或 Private Support。
- 沒有 compact migration dry-run/apply/no-op receipt 時，不得執行真實 cloud smoke。
