# Google Sheets／GAS 儲存與同步選項

本文件不預設一定需要 VPS 或 always-on 主機。目標是分析如何以 GSheet／GAS、間歇 bot 與每週維護取得可接受的效能與可靠度。

## 1. 設計目標

- 網頁查詢不重新演算完整 Discord history。
- Active case 查詢快速。
- Bot 不必高頻輪詢。
- 每週可執行完整 dump／分析／封存。
- Working data 與 long-term archive 分離。
- Bot 暫時離線時可降級運作。
- 不把 Apps Script 描述成 robust server database。

## 2. 建議資料分層

Working Sheet：Users、Classes、ActiveCases、CaseProjection、Consent、SyncState、ChangedCaseQueue、Settings。

Archive Sheet／Index：ArchiveIndex、ClosedCases、WeeklyRuns、ExportManifests、AnalysisReports。

一個 active case 盡量是一列或少量列；完整長對話不一定全部塞入同一張 working sheet。

## 3. CaseProjection

網站主要讀：

```text
case_number
masked_case_number
status
last_update_at
last_response_at
latest_response_excerpt
timeline_summary
attachment_count
discord_thread_id
discord_deep_link
ai_analysis_allowed
closure_source
```

這樣網頁不需要每次叫 Discord 重算。

## 4. Bot 是否要常駐

### 方案 A：常駐 Gateway Bot

優點：即時接收變更，不需輪詢，projection 接近即時。

缺點：需要穩定主機與維運。

### 方案 B：課程時段／每日固定開啟

優點：不必 24/7，可由本機或借用主機執行，適合早期試驗。

缺點：離線期間不會收到 Gateway event，上線後要 reconciliation，網頁資料可能短暫落後。

### 方案 C：主要靠 on-demand fetch

優點：平時不需常駐，只有查詢單一案件時工作。

缺點：每次查詢需外部服務，Apps Script 不適合直接承擔 Python Discord Gateway，延遲與 quota 需測試。

### 早期建議

先做 B：課程與 TA 使用時段開啟；每日或每週 reconciliation；網頁顯示 Last Synced；允許資料延遲；等真實使用量證明需要，再決定是否常駐。

## 5. GAS Trigger 適合做什麼

適合：結案規則檢查、每日摘要、清理過期 verification nonce、將 closed case 移到 archive index、寄有限量通知、檢查 sync age、建立每週 maintenance task。

不適合：維持 Discord Gateway、大量即時訊息 ingest、長時間 Python 工作、啟動一般 Colab 當 production server。

## 6. Colab

適合人工啟動的分析 notebook、週報產生與 sanitized data 批次分析。

不適合 24/7 Discord bot、穩定 webhook endpoint 或持久 backend。因此 GAS 不應依賴「喚醒 Colab」作為核心 production 路徑。

## 7. Google Workspace

購買 Workspace 可能提高 Email recipient、Trigger runtime 與 URL Fetch 配額，但不會取消單次 Apps Script execution 限制，也不會讓 GAS 變成常駐 Python server。

早期不必因 prototype 先買 Workspace。先量測學生數、每日 Email 驗證量、案件查詢量、Trigger runtime 與 Sheet row growth。

## 8. GSheet 變肥的控制

1. Active cases 與 closed cases 分開。
2. 每學期分 spreadsheet 或 archive partition。
3. 每週 rollover。
4. 完整訊息只保留必要 projection。
5. Raw dump 另存 JSON／Markdown。
6. Sheet 只保留 archive pointer。
7. 建立 row count／size diagnostics。
8. 寫入 idempotency key。
9. 定期 compact 或建立新 working sheet。
10. 不在單一 cell 塞入巨大完整 thread。

## 9. 每週維護

```text
1. Reconcile active cases
2. Update projections
3. Apply temporary／automatic close
4. Dump selected or changed threads
5. Generate sanitized package
6. Produce teaching analysis
7. Update ArchiveIndex
8. Record maintenance run
9. Check quota and sheet growth
10. Produce diagnostic report
```

早期可由人工啟動，不必全部自動。

## 10. 網頁查詢降級

Bot 離線時：顯示 GSheet projection、顯示 Last Synced、允許前往 Discord、不宣稱即時；必要時提供「要求更新」旗標，待 bot 下次上線同步。

## 11. 仍需技術 spike

- GAS query latency。
- Sheet row growth。
- Apps Script trigger 成本。
- Discord on-demand REST fetch。
- Bot 離線後 reconciliation。
- 一週案件量。
- 附件與長訊息對 projection 的影響。
- 是否需要 SQLite／PostgreSQL 中介。
