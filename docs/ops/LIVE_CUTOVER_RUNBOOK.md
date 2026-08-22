# Live Cutover Runbook

## 前置必須全部 PASS

```text
SSH/host        PASS
remote staging  PASS
Google bridge   PASS
OAuth longevity PASS（Production，或已接受每 7 天人工重授權）
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
10. remote heartbeat 穩定後才啟用 bound GAS status digest；若授權仍是 Testing，先確認重授權責任人與失效處置。

## Rollback

遇 migration 不一致、登入失敗、重複副作用、DB corruption、queue critical failure、secret 缺漏或 duplicate process，立刻停止所有 remote unit。決定回 Mac 時，remote 必須保持 stopped，再用未修改 rollback DB 恢復單一 writer。

## Cutover 後 lifecycle UX 修復換版

第一次修復換版同時安裝 `docs/ops/RESTRICTED_DEPLOYMENT_ENTRYPOINT.md` 定義的受限入口；之後一般
production release 使用 root-owned `/usr/local/sbin/calculus-discord-deploy`。入口只接受固定 inbox、
release checksum 所涵蓋的 exact-pinned dependency lock、正確 hostname、單一步 additive migration
與無參數 invocation。它不改 OAuth／Discord secrets，也不重跑舊的 compact migration、GAS parity、
local smoke、synthetic cleanup 或 recovery rehearsal。

執行前先在非 root staging 完成 source transfer、測試與 checksum；首次 bootstrap 最後只需一次 sudo。
builder 在無 production DB／secret 權限下建立新 venv，再用 consistent DB copy 驗證 migration；直到
這些 gate 全過才短暫停止服務。正式 migration、三服務 fresh health 或 integrity 任一失敗時，自動恢復
舊 release 與 pre-upgrade DB。
