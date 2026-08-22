# 24 小時主機部署

## 固定架構

- 經人工核對 host key 的固定 SSH endpoint 與 systemd Linux；本專案不依賴 Tailscale。
- project owner 以 SSH key 管理；`calculus-bot` 是無 shell、無 sudo 的 service account。
- release：`/opt/calculus-discord/releases/<git-sha>`，`current` 指向單一已驗證 release。
- SQLite：`/var/lib/calculus-discord/runtime.sqlite3`；三個服務共用此 authority。
- secret：`/etc/calculus-discord/*.env` 與 `google-oauth.json`，不得進 Git 或 journald。

## 執行順序

1. 在本機確認 clean commit，建立可驗證 artifact。
2. 第一次 SSH 嚴格核對 host key；執行 `ops/scripts/phase2c-host-audit.sh`。
3. audit 通過後才執行 `install-host-skeleton.sh`。
4. 安裝 release-specific `.venv`，不得 global pip install。
5. 先建立 `/var/lib/calculus-discord/staging/phase2b-data-lab/staging.sqlite3`；保持 `STAGING`、`synthetic_only=1`、`live_discord_enabled=0`。
6. 安裝但不啟用三個 unit；先跑 staging、real-Google 與 backup/restore rehearsal。
7. 只有收到精確 `GO-LIVE-CUTOVER` 才依 cutover runbook 搬 live DB 與啟動 production。

## 驗收

```bash
systemctl is-active calculus-course-assistant calculus-dump-bot calculus-data-bridge
systemctl is-enabled calculus-course-assistant calculus-dump-bot calculus-data-bridge
journalctl -u calculus-data-bridge --since -10min --no-pager
sqlite3 /var/lib/calculus-discord/runtime.sqlite3 'PRAGMA integrity_check;'
```

輸出只能保留服務狀態與安全錯誤碼，不得貼 token、OAuth credential、Discord ID 或資料列內容。
