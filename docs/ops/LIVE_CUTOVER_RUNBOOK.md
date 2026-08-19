# Live Cutover Runbook

## 前置必須全部 PASS

```text
SSH/host        PASS
remote staging  PASS
Google bridge   PASS
cloud smoke     PASS
backup restore  PASS
DB rehearsal    PASS
rollback        READY
```

在使用者尚未回覆精確 `GO-LIVE-CUTOVER` 前，不停 Mac Bot、不搬 live DB、不啟動 remote production。

## Cutover

1. 記錄時間；停止 Mac 的 course_assistant、dump_bot 與任何 DB writer。
2. 證明舊 writer 數量為 0；不得先啟動 remote Bot 試跑。
3. 以 SQLite consistent backup 建 owner-only rollback copy，記錄 SHA-256。
4. 安全傳輸 DB 與必要 env；兩端 checksum 必須一致，remote 檔案 0600。
5. 在 transferred copy migrate 到 current；`integrity_check`、migration ledger、inspector 都要 PASS。
6. atomic move 成 `/var/lib/calculus-discord/runtime.sqlite3`。
7. 固定啟動：course_assistant → health → dump_bot → health → data_bridge。
8. 驗證舊 writer=0、remote process=預期數、systemd enabled、只有 remote 使用 production DB。
9. 建立一筆 allowlisted Public smoke；不得建立真人 Private 資料。

## Rollback

遇 migration 不一致、登入失敗、重複副作用、DB corruption、queue critical failure、secret 缺漏或 duplicate process，立刻停止所有 remote unit。決定回 Mac 時，remote 必須保持 stopped，再用未修改 rollback DB 恢復單一 writer。
