# v13 Deployment Safety Runbook

狀態：`LOCAL_GATES_PASS / FREEZE_VIA_EXTERNAL_RELEASE_EVIDENCE / HOST_OWNER_PREPARE_PENDING`。舊
`3411aff` request 已可逆封存；只有 external release evidence 綁定的 exact clean commit、archive SHA-256
與 host-owner prepare receipt 完成後，才建立新的 remote request。

本輪安全決策：移除未納管的 `GET /api/cases/status` 旁路；草稿刪除失敗只回固定訊息；Private
Support 在無唯一班級 mapping 時保留受控 module metadata fallback。Private 頻道 ACL 仍只由 Discord
overwrites 決定，不由 module metadata 決定。Private 在 48＋48 自動結案，或手動結案滿 48 小時後，
先執行 verified dump；只有 manifest 驗證成功才刪除受限頻道。

## 0. 固定邊界

- Production 仍是 remote Linux、schema v6；SQLite 是唯一 operational authority。
- 唯一 production writer 必須是 remote 的三個 systemd services：`calculus-course-assistant.service`、`calculus-dump-bot.service`、`calculus-data-bridge.service`。Mac writer 必須維持停止。
- v13 deployment 目標為 schema v13；migration 必須在 consistent backup 的可拋棄副本完成後，才可進入 owner 的 deploy decision。
- 不把 raw SQLite rows、案件內容、學生／TA／教師 IDs、secrets 或附件放入 receipt、Git 或聊天。

## 1. Host owner 單次 prepare

Codex／PM 提供 exact Git archive、standalone bootstrap 與兩者的 SHA-256。將兩檔放進既有 upload
root 後，朋友只執行下列一個 root command 一次。Launcher 先把 bootstrap 複製到 `/run` 的 root-only
暫存目錄，驗證該可信副本的 SHA-256，再由系統 `/bin/bash` 讀取它。這樣不依賴
`/run` 是否允許 direct exec，也不會直接從 `ding` 可寫的 upload path 開啟腳本：

```bash
sudo env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin LC_ALL=C \
  V13_RELEASE_ID=<exact-release> \
  V13_BOOTSTRAP_SHA256=<bootstrap-sha256> \
  V13_ARCHIVE_SHA256=<archive-sha256> /bin/bash <<'V13_ROOT'
set -euo pipefail
umask 077
launcher_error() {
  trap - ERR
  printf 'v13_launcher=FAIL\nsafe_error_code=TRUSTED_COPY_OR_INPUT_INVALID\n' >&2
  printf 'deploy_executed=NO\n' >&2
  exit 2
}
trap launcher_error ERR
[[ $V13_RELEASE_ID =~ ^[a-f0-9]{12}$ ]]
[[ $V13_BOOTSTRAP_SHA256 =~ ^[a-f0-9]{64}$ ]]
[[ $V13_ARCHIVE_SHA256 =~ ^[a-f0-9]{64}$ ]]
source=/home/ding/calculus-discord-staging/v13-friend-bootstrap.sh
archive=/home/ding/calculus-discord-staging/v13-release-$V13_RELEASE_ID.tar
[[ -f $source && ! -L $source ]]
[[ -f $archive && ! -L $archive ]]
[[ $(stat -c %s "$source") -le 1048576 ]]
[[ $(stat -c %s "$archive") -le 104857600 ]]
trusted_dir=$(mktemp -d /run/v13-bootstrap.XXXXXXXX)
trap 'rm -rf -- "$trusted_dir"' EXIT
trusted=$trusted_dir/v13-friend-bootstrap.sh
install -o root -g root -m 0700 "$source" "$trusted"
printf "%s  %s\n" "$V13_BOOTSTRAP_SHA256" "$trusted" | sha256sum -c -
if ! BOOTSTRAP_V13_RELEASE=BOOTSTRAP-V13-RELEASE \
  /bin/bash -- "$trusted" "$archive" "$V13_ARCHIVE_SHA256" "$V13_RELEASE_ID"; then
  exit 2
fi
V13_ROOT
```

Bootstrap 會先確認 host `python3` 符合 runtime 明訂的 `>=3.12,<3.15`，再以單一 file descriptor
驗證 archive 是 regular file、SHA-256、Git commit、path traversal、檔案型別、
數量與大小，再 atomic stage 到 root-owned、`ding` 不可寫的 trusted release root。Stage receipt 綁定 full
commit、archive SHA-256 與完整 tree digest；同一 exact release 可安全 resume，root 不從 upload root 執行或
import candidate code。接著 owner prepare 在任何 production mutation 前先檢查
exact path、critical files、archive tree、dependency lock、
deployer old/new/unknown 狀態、sudoers、users、directories、三服務 active／enabled／service user、runtime
env owner/mode/必填值、`BOT_OWNER_IDS` bootstrap，以及 production DB owner/mode/integrity/foreign keys／
schema v6／migration names+checksums、fresh health／既有 failure queues、磁碟空間與 inode。只接受已知舊
deployer 或同一 candidate deployer；其他狀態 fail closed。

所有前置條件通過後，它只會 idempotent repair root-owned deployer、建立 consistent backup 與獨立 v6→v13
rehearsal receipt，並將既有三個 runtime env 檔案從 `calculus-bot:calculus-bot 0600` 正規化為
`root:root 0600`（只改 owner metadata，不改 secret values；systemd 仍可讀取）。Backup／receipt 位於
`/var/lib/calculus-discord-deploy` 的 root-only namespace，不放在 service-owned backups 目錄。它不
stop/start service、不切 symlink、不 migrate production、不建立 deploy request。Fresh
與 exact resume 都必須包含完整成功欄位；只接受：

```text
v13_host_prepare=PASS 或 ALREADY_READY
backup_rehearsal=PASS
deployer=READY
runtime_env_ownership=HARDENED 或 ALREADY_ROOT_OWNED
production_database_modified=NO
v13_friend_bootstrap=PASS
release_staged=PASS 或 ALREADY_STAGED
deploy_executed=NO
```

只要 command 非零退出、提前回到 prompt、輸出 `FAIL`，或必要 PASS 欄位少一個，都視為失敗；朋友不要
自行清檔、修權限、改 user 或重跑。PM 先用 receipt
與 exact source 修完同類問題，再決定是否需要新的 owner 窗口。重貼舊 phase2c 指令一律禁止。

## 2. Mapping gate

先執行不含真實 IDs 的 mapping shape 檢查：

```bash
python3 ops/scripts/validate-v13-mapping.py \
  config/release/v13-production-mapping.template.json \
  --allow-pending
```

Live Guild 的 course／visitor role、C01–C16、三個 managed forums 與 Private category 已完成 provisioning，
read-only verify 為 0 error／0 warning；真實 IDs 只在 mode `0600` secure mapping。由於 production v6 尚無
`reviewer_grants` table，predeploy gate 是 host prepare 確認 `BOT_OWNER_IDS` bootstrap 非空；explicit reviewer／
system-admin grants 是 migration 後、rollout 前 gate。

## 3. Owner deploy decision 與單一路徑部署

Checkpoint 與 deployment 都在 `jerrymk-workstation` 執行。使用者的 Mac 只負責準備、
測試、凍結與審閱 exact 交付，不會直接操作 production host。最終外部 handoff
必須綁定 exact release ID、archive SHA-256 與 owner deploy approval；Jerrymk 或其 Codex
只在 host checkpoint 全部 PASS 後才能繼續。

Release 與 request 可先在非 production staging 完成 checksum 固定；只有 production backup rehearsal、
mapping gate 與 PM／課程 owner 對該 exact release 的明示 deploy 授權全部通過後，才可執行 restricted
deployer：

1. 核對 root-owned trusted release 中的 original archive、dependency lock、release ID、SHA-256 與
   friend preflight receipt；固定 inbox 只接受四欄 request，不接受第二份 user-owned archive。
2. 以 `ops/scripts/prepare-calculus-discord-deploy-request.sh` 產生四欄 request：release、archive SHA-256、target schema `13`、migration class `ADDITIVE`；deployer 只接受經 rehearsal 的 exact v6→v13 chain，不接受任意 additive target。
3. 由既有 root-owned `/usr/local/sbin/calculus-discord-deploy` 執行唯一 production cutover；操作者不直接執行 archive 內任意 script，也不自行切換 `/opt/calculus-discord/current`。
4. Deployer 先驗證 current schema／ledger、release checksum、builder workspace 與 verified-copy migration；全部通過後才短暫停止三服務。
5. Deployer 保存 pre-deploy rollback DB，再以單一 writer 完成 v6 → v13，atomic 切換 release。
6. 依固定順序啟動並等 fresh health：course assistant → dump bot → data bridge。

## 4. Deployment smoke 與 manual attention

Smoke 只核對 metadata／health，不建立真人 Private 資料、不輸出 raw rows：

```bash
DB=/var/lib/calculus-discord/runtime.sqlite3
for unit in calculus-course-assistant.service calculus-dump-bot.service calculus-data-bridge.service; do
  systemctl is-active "$unit"
done
sqlite3 "$DB" 'PRAGMA integrity_check; PRAGMA user_version;'
sqlite3 "$DB" 'SELECT COUNT(*) FROM schema_migrations;'
sqlite3 "$DB" "SELECT service_key, status, safe_error_code FROM service_health ORDER BY service_key;"
sqlite3 "$DB" "SELECT 'discord_lifecycle', COUNT(*) FROM discord_lifecycle_jobs WHERE status IN ('RETRYABLE_FAILURE','PERMANENT_FAILURE') UNION ALL SELECT 'dm_outbox', COUNT(*) FROM discord_dm_outbox WHERE status IN ('RETRYABLE_FAILURE','PERMANENT_FAILURE') UNION ALL SELECT 'course_role', COUNT(*) FROM course_role_jobs WHERE status IN ('RETRYABLE_FAILURE','PERMANENT_FAILURE') UNION ALL SELECT 'private_open', COUNT(*) FROM private_open_requests WHERE status IN ('RETRYABLE_FAILURE','PERMANENT_FAILURE') UNION ALL SELECT 'private_dump', COUNT(*) FROM private_dump_jobs WHERE status = 'FAILED' UNION ALL SELECT 'email', COUNT(*) FROM email_delivery_outbox WHERE status IN ('RETRYABLE_FAILURE','PERMANENT_FAILURE') UNION ALL SELECT 'projection', COUNT(*) FROM projection_outbox WHERE status IN ('RETRYABLE_FAILURE','PERMANENT_FAILURE');"
```

另由 bootstrap owner 執行 `/ops status` 與 `/ops attention-list`；後者必須回報沒有未解決人工接管項目。
`safe_error_code` 與 critical queue 必須為零；任何 retryable／permanent failure 先保留安全摘要並停線，
不重複送出副作用。白帳號 E2E、Discord ACL 與 Portal backend 仍是另外的 rollout gate。

## 5. Rollback

任一時點出現 migration mismatch、checksum／integrity failure、fresh health timeout、duplicate writer、queue critical failure、secret 缺漏、重複副作用或必要 mapping 缺漏：

1. 立即停止三個 remote services，確認 remote writer=0。
2. 保留未修改的 pre-deploy rollback DB 與 receipt；不得把 migrated DB 當 rollback source。
3. 由 restricted deployer restore 舊 release symlink 與 rollback DB，清除 WAL／SHM sidecar 後 atomic replace。
4. 只有舊 symlink、rollback DB、`integrity_check`、schema v6、ledger 1–6 全部恢復後才啟動舊 release 的三服務。
5. 任一步失敗輸出 `rollback=FAILED_SERVICES_STOPPED` 並維持 services stopped，交由 host owner 處理；不得自行重試 destructive action。

## 6. Backup retention

Pre-deploy rollback DB、checksum receipt 與 deploy／rollback audit 必須保留到 owner 明示 v13 smoke、白帳號 E2E、rollback readiness 與 observation window 已接受。Owner 已決定：小型 Private export 可暫存 remote；大型附件先拉回本地並驗證完整接收，再刪 remote copy。
