# v10 Release Safety Runbook

狀態：`SECURITY_REVIEWED / RELEASE_STAGED / PRODUCTION_V6_UNCHANGED`。舊 `3411aff` request 已可逆封存；
目前 staging request 指向修補後的 exact commit，release ID 與 SHA-256 以 remote `request.txt` 為準。
restricted deployer 已就緒，但尚未執行；沒有重啟、live migrate、套用 Discord mapping 或修改
production DB。

本輪安全決策：移除未納管的 `GET /api/cases/status` 旁路；草稿刪除失敗只回固定訊息；Private
Support 在無唯一班級 mapping 時保留受控 module metadata fallback。Private 頻道 ACL 仍只由 Discord
overwrites 決定，不由 module metadata 決定。48＋48 代表自動結案，不代表自動刪除頻道。

## 0. 固定邊界

- Production 仍是 remote Linux、schema v6；SQLite 是唯一 operational authority。
- 唯一 production writer 必須是 remote 的三個 systemd services：`calculus-course-assistant.service`、`calculus-dump-bot.service`、`calculus-data-bridge.service`。Mac writer 必須維持停止。
- v10 product candidate 目標為 schema v11；migration 必須在 consistent backup 的可拋棄副本完成後，才可進入 owner 的 deploy decision。
- 不把 raw SQLite rows、案件內容、學生／TA／教師 IDs、secrets 或附件放入 receipt、Git 或聊天。

## 1. Preflight：只讀核對

由 host owner 在 production host 執行；`DB`、`BACKUP`、`WORK` 與 `RECEIPT` 必須是 owner-only 路徑：

```bash
DB=/var/lib/calculus-discord/runtime.sqlite3
BACKUP=/var/lib/calculus-discord/backups/v10-preflight.sqlite3
WORK=/var/lib/calculus-discord/staging/v10-release-safety
RECEIPT=/var/lib/calculus-discord/receipts/v10-release-safety.json

readlink -f /opt/calculus-discord/current
for unit in calculus-course-assistant.service calculus-dump-bot.service calculus-data-bridge.service; do
  systemctl is-active "$unit"
  systemctl is-enabled "$unit"
done
sqlite3 "$DB" 'PRAGMA integrity_check; PRAGMA user_version;'
sqlite3 "$DB" 'SELECT COUNT(*) FROM schema_migrations;'
```

只接受：三服務 `active`／`enabled`、`integrity_check=ok`、schema／ledger 都是 v6、current 是預期 release、且沒有第二個 writer。不能證明單一 writer 時立即停止。

## 2. Production consistent backup-copy rehearsal

先由 owner 在服務仍受控運作的狀態取得 consistent backup；不得把工作副本直接當 production DB：

```bash
install -d -m 0700 "$WORK"
rm -f -- "$BACKUP"
sqlite3 "$DB" ".backup '$BACKUP'"
chmod 0600 "$BACKUP"
python3 ops/scripts/sqlite-recovery-rehearsal.py \
  "$BACKUP" "$WORK" \
  --expected-source-schema 6 \
  --expected-target-schema 11 \
  >"$RECEIPT"
```

`PASS` 必須同時滿足：backup 可讀、source／backup／restore `integrity_check=ok`、source schema v6、source ledger 1–6 完整、candidate ledger 1–10 完整、所有既有 table row counts 不變、migration 只發生在副本、rollback copy 與 pre-migration backup 等價、workspace 可寫且資料庫 owner-only、source checksum 在演練前後不變。Receipt 僅含 schema、count、health、mode 與 SHA-256。

演練結束後不保留副本：

```bash
find "$WORK" -mindepth 1 -maxdepth 1 -type d -exec rm -rf -- {} +
```

若 backup 不可讀、任何 integrity／ledger／count／rollback gate 失敗，或清理責任不明，保持 `FAIL_CLOSED`，不進入 deploy request。

## 3. Mapping gate

先執行不含真實 IDs 的 mapping shape 檢查：

```bash
python3 ops/scripts/validate-v10-mapping.py \
  config/release/v10-production-mapping.template.json \
  --allow-pending
```

只有 owner 以受控 runtime 設定提供 guild、course／visitor role、C01–C16 class roles、三個 managed forums、Private category 與 reviewer／system-admin grants 後，才可將 receipt 改為 `PASS`。真實值不得回填 tracked template；mapping 的必填項與已知缺值見 `docs/ops/V10_PRODUCTION_MAPPING_CHECKLIST.md`。

## 4. Owner deploy decision 與單一路徑部署

Release 與 request 可先在非 production staging 完成 checksum 固定；只有 production backup rehearsal、
mapping gate 與 PM／課程 owner 對該 exact release 的明示 deploy 授權全部通過後，才可執行 restricted
deployer：

1. 核對固定 inbox 中 exact release archive、dependency lock、release ID 與 SHA-256。
2. 以 `ops/scripts/prepare-calculus-discord-deploy-request.sh` 產生四欄 request：release、archive SHA-256、target schema `10`、migration class `ADDITIVE`。
3. 由既有 root-owned `/usr/local/sbin/calculus-discord-deploy` 執行唯一 production cutover；不直接執行 archive 內任意 script，不切換 `/opt/calculus-discord/current`。
4. Deployer 先驗證 current schema／ledger、release checksum、builder workspace 與 verified-copy migration；全部通過後才短暫停止三服務。
5. Deployer 保存 pre-deploy rollback DB，再以單一 writer 完成 v6 → v10，atomic 切換 release。
6. 依固定順序啟動並等 fresh health：course assistant → dump bot → data bridge。

## 5. Deployment smoke 與 manual attention

Smoke 只核對 metadata／health，不建立真人 Private 資料、不輸出 raw rows：

```bash
for unit in calculus-course-assistant.service calculus-dump-bot.service calculus-data-bridge.service; do
  systemctl is-active "$unit"
done
sqlite3 "$DB" 'PRAGMA integrity_check; PRAGMA user_version;'
sqlite3 "$DB" 'SELECT COUNT(*) FROM schema_migrations;'
sqlite3 "$DB" "SELECT service_key, status, safe_error_code FROM service_health ORDER BY service_key;"
sqlite3 "$DB" "SELECT 'discord_lifecycle', COUNT(*) FROM discord_lifecycle_jobs WHERE status IN ('RETRYABLE_FAILURE','PERMANENT_FAILURE') UNION ALL SELECT 'dm_outbox', COUNT(*) FROM discord_dm_outbox WHERE status IN ('RETRYABLE_FAILURE','PERMANENT_FAILURE') UNION ALL SELECT 'course_role', COUNT(*) FROM course_role_jobs WHERE status IN ('RETRYABLE_FAILURE','PERMANENT_FAILURE') UNION ALL SELECT 'private_open', COUNT(*) FROM private_open_requests WHERE status IN ('RETRYABLE_FAILURE','PERMANENT_FAILURE');"
```

`safe_error_code`、manual attention 與 critical queue 必須為零；任何 retryable／permanent failure 先保留安全摘要並停線，不重複送出副作用。白帳號 E2E、Discord ACL 與 Portal backend 仍是另外的 owner gate，不由本 runbook 的本機 PASS 取代。

## 6. Rollback

任一時點出現 migration mismatch、checksum／integrity failure、fresh health timeout、duplicate writer、queue critical failure、secret 缺漏、重複副作用或必要 mapping 缺漏：

1. 立即停止三個 remote services，確認 remote writer=0。
2. 保留未修改的 pre-deploy rollback DB 與 receipt；不得把 migrated DB 當 rollback source。
3. 由 restricted deployer restore 舊 release symlink 與 rollback DB，清除 WAL／SHM sidecar 後 atomic replace。
4. 只啟動舊 release 的三服務，重新核對 `integrity_check`、schema／ledger、health、queue 與 single-writer。
5. rollback 失敗時維持 services stopped，交由 host owner 處理；不得自行重試 destructive action。

## 7. Backup retention

Pre-deploy rollback DB、checksum receipt 與 deploy／rollback audit 必須保留到 owner 明示 v10 smoke、白帳號 E2E、rollback readiness 與 observation window 已接受。保留期限尚未被治理 owner 明確核准，因此本 release 不自動刪除 backup；未指定 retention owner 或期限即 `FAIL_CLOSED`。
