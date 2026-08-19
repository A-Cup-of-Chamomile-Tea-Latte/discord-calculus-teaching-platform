# Phase 2C：24h Host、GAS／SQLite／Discord 正式聯動報告

> 更新時間：2026-08-19 19:16 Asia/Taipei  
> Branch：`codex/phase-2c-24h-production-integration`  
> 已驗證程式 HEAD：`0d91ccd`  
> 本文件會在 remote gate 完成後原地更新，不另生重複版本。

## 十分鐘白話版

1. 兩隻 Discord Bot 目前仍由這台 Mac 的 LaunchAgent 管理，各只有一個 process，沒有進行 live cutover。
2. Local SQLite 是唯一 operational authority；Google Sheets 只是精簡、人可閱讀的投影，不是另一套主資料庫。
3. 本機已透過 owner-only Desktop OAuth 與 Apps Script API `scripts.run` 連到 standalone GAS，不使用公開 endpoint。
4. `Server Database` 已收斂為 5 個人用頁與 5 個隱藏機器頁；舊的 21 個空受管頁已由安全 migration 清除。
5. 真實 cloud smoke 已用一筆 synthetic fixture 通過：preview、apply、outbox complete、重跑 no-work 全部正確。
6. Google 掛掉時 Discord 仍先寫 SQLite；投影留在可靠 outbox，不會因 Sheet 暫時不可用而停止案件服務。
7. 新 Linux host 的 systemd、backup、restore 與 cutover tooling 已在 repo，但尚未收到 SSH／Tailscale target，不能假裝已部署。
8. 未收到精確字串 `GO-LIVE-CUTOVER` 前，不會停止 Mac writer、搬 live DB 或啟動 remote production writer。
9. OAuth client 與 authorized-user credential 都在 `.local/phase2c-oauth/`，權限為 `0600`、不進 Git、Sheet、報告或交接包。
10. 下一個唯一外部需求是 24h host 的 SSH username、Tailscale hostname／IP 與預期 host-key fingerprint。

## 本輪完成

- 修復 Mac LaunchAgent 的 macOS TCC log-path 問題，兩隻 Bot 恢復單一實例並持續 active。
- SQLite v5：production lifecycle event、service health、production projection stream；案件異動與 outbox 同 transaction。
- Apps Script transport：token 於記憶體刷新、固定 Google endpoint、credential 不寫 log、Google failure 回安全代碼。
- Bridge daemon：60 秒 projection、batch ≤50、Google failure degraded、graceful SIGTERM、production command inbox fail-closed。
- Sheet migration：第一次 dry-run 44 項、apply 44 項、第二次 dry-run no-op。
- GAS status digest：07:00／13:30／19:00 slot、5 分鐘 dispatcher、NORMAL／ATTENTION／CRITICAL、at-most-once receipt。
- systemd units、host audit、host skeleton、SQLite consistent backup、restore rehearsal 與 guarded cutover scripts。
- 建立 standard GCP project、外部測試 OAuth、Desktop client；Apps Script API 已啟用。
- 將 standalone manifest 從歷史 `webapp` 修正成真正 `executionApi`；immutable deployment 更新至 v7。
- 新增 fail-closed `bridgeConfigureTarget`：驗證 10 個 canonical tabs 後才寫 Script Properties，並刪除舊 `PHASE2B_*` property。
- 真實 `scripts.run` health、preview、apply、idempotency 均通過。

## 真實 cloud smoke 收據

| 檢查 | 結果 |
|---|---|
| OAuth credential | refresh token 存在；scope 只有 Google Sheets；檔案 `0600` |
| `bridgeHealth` | `ok=true`、`STAGING`、`syntheticOnly=true`、schema `2.0.0` |
| Synthetic preview | `SYNC_PREVIEW_READY`；4 筆 pending；無 cloud mutation |
| Synthetic apply | `SYNC_APPLIED`；4 筆完成；經 `APPS_SCRIPT_API` |
| Idempotency | 第二次 dry-run：`PROJECTION_QUEUE_EMPTY` |
| Local outbox | `COMPLETED=4` |
| Sheet 範圍 | `CaseBoard=1`、`History=1`、`Operations=1`、`Overview=2`；皆為 synthetic fixture |

## 驗證收據

| 項目 | 結果 |
|---|---|
| Runtime tests | 74 passed |
| Ruff check／format | PASS |
| GAS tests | 58 passed |
| GAS typecheck | PASS |
| GAS standalone build | PASS |
| Sheet migration dry-run／apply／no-op | PASS |
| Mac Bot single-instance | PASS |
| Git diff check | PASS |

## Gate 狀態

| Gate | 狀態 | 說明 |
|---|---|---|
| Local baseline／implementation | PASS | 可稽核 commits；tests green |
| Compact Sheet | PASS | 44 → apply → no-op；5 visible + 5 hidden |
| Google OAuth transport | PASS | Desktop OAuth、standard GCP、`scripts.run` health 均通 |
| Local real-cloud synthetic round-trip | PASS | preview／apply／no-work 均通 |
| SSH／Tailscale | BLOCKED | 尚未提供 target 與 host key |
| Remote staging | BLOCKED | 等 SSH；不得把 Mac smoke 說成 remote smoke |
| Backup／restore rehearsal | BLOCKED | tooling ready；等 remote staging |
| Live cutover | NOT STARTED | 必須等精確 `GO-LIVE-CUTOVER` |
| 24h observation | NOT STARTED | 只能在 cutover 後按實際 24 小時計時 |
| GAS status digest | TESTED, NOT ENABLED | 等 remote heartbeat 穩定後再安裝 trigger，避免假警報 |

## 實測中排除的歷史瑕疵

- `clasp --auth ntusupercool` 是錯誤用法；v3.3 應使用 `-u ntusupercool`。已修正操作流程，沒有重做登入。
- standalone manifest 原為 `webapp`，部署名稱雖寫 API executable，實際 `scripts.run` 會 404。已換成官方 `executionApi` manifest。
- target 初始化曾手動重複 machine-tab 名單並與 schema 漂移。現改由 `SHEET_SCHEMAS` 單一來源產生，避免再次分裂。
- Google execution error 缺少 `status` 時，舊程式會顯示無意義的 `NONE`。現會保留 allowlisted safe error code，CLI 不再輸出 traceback。
- Drive connector 登入的是另一個帳號；未採用其搜尋結果。最終以已確認的 project-account clasp OAuth 做唯讀 metadata 定位。

## 時間紀錄與估計校正

| 節點 | 原估 | 實際／狀態 |
|---|---:|---:|
| Mac Bot 修復 | 15–30 分 | 約 4 分 |
| Local Phase 2C 第一版 | 2–4 小時 | 18:04–18:33，約 29 分 |
| GCP／OAuth／GAS executable／cloud smoke | 未單列 | 約 18:56–19:14，約 18 分；含兩次 fail-closed 修正 |
| Remote deployment（取得 SSH 後） | 1–2 小時 | 尚未開始 |
| Post-cutover observation | 24 小時實時 | 尚未開始 |

較快是因為 Phase 2B 的 migration、queue 與 compact schema 可直接延伸；驗收範圍沒有縮減。Remote deployment 與 24 小時觀察不能用本機測試替代。

## 下一個唯一外部輸入

請提供：

1. 24h host 的 SSH username。
2. Tailscale hostname 或私網 IP。
3. 預期 SSH host-key fingerprint；若尚未記錄，請在第一次連線時由你人工核對。

收到後先做唯讀 host audit 與 remote staging，不會直接 live cutover。

## 最終回報欄位（remote gate 後原地覆寫）

1. local branch／已驗證程式 HEAD：`codex/phase-2c-24h-production-integration`／`0d91ccd`
2. remote release SHA：BLOCKED
3. SSH／Tailscale：BLOCKED
4. remote staging：BLOCKED
5. Google OAuth transport：PASS
6. local real-cloud synthetic round-trip：PASS
7. remote real-cloud synthetic round-trip：BLOCKED
8. backup／restore：BLOCKED
9. live cutover：NOT STARTED
10. course_assistant：Mac RUNNING
11. dump_bot：Mac RUNNING
12. data_bridge：NOT STARTED
13. GAS status digest：TESTED／NOT ENABLED
14. secrets findings：0
15. 使用者下一個唯一操作：提供 SSH／Tailscale target 與 host-key fingerprint
