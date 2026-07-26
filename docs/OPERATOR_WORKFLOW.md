# 操作員流程：dump、follow、review 與 import

## 適用範圍

本文件只示範 fixtures 與 local adapters。`dump` / `follow` 不是掃描整個 Discord server 的指令，也不是常駐監控。正式 Discord reader、manager authentication、durable audit 與 Google destination 仍未實作。

## 每次執行前

1. 確認操作者已獲授權，且範圍只有一個明確選定的 general case/thread。
2. 確認該案件不是 Private Support，並理解 raw export 可含 EXCLUDED 內容。
3. 確認 output root 是本機、Git-ignored、存取受控、不同步到公開 cloud folder。
4. 確認只使用 fixture adapter；未經授權不設定 live credentials。

## A. Dump：建立完整快照

```sh
source .venv/bin/activate
python -m tools.discord_export C01-7K4M2Q-0702-1000 \
  --adapter fixture \
  --output-dir exports \
  --page-size 2
```

檢查 `exports/C01-7K4M2Q-0702-1000/` 內四檔：

- `thread.json`：raw ordered messages；
- `thread.md`：人可讀討論與 reply context；
- `metadata.json`：export manifest、cursor、file hashes、analysis policy；
- `attachments.json`：metadata-only attachment index，無 URL/binary download。

再執行相同命令應回報 `unchanged: true`。若內容不同或 partial file set/hash 無法驗證，停止並先調查，不手動接起不一致的 JSON。

## B. Follow：以 checkpoint 增量取得

`metadata.json` 的 `cursor` 是上次最後一則 Discord message ID。只能明確傳入與現有 manifest 完全相同的 checkpoint：

```sh
python -m tools.discord_export C01-7K4M2Q-0702-1000 \
  --adapter fixture \
  --output-dir exports \
  --after-message-id 423456789012345681
```

重要限制：

- Follow 只看到 checkpoint 之後的新訊息，看不到較舊訊息後來的 edit。
- 需要 reconciliation 時，以不帶 checkpoint 的 explicit full dump 更新快照。
- 不要用 shell loop/cron 把這個單次命令變成未審核的持續監控。

## C. Consent 與去識別化

```sh
python -m tools.anonymizer \
  exports/C01-7K4M2Q-0702-1000 \
  --output-dir local-data/sanitized
```

檢查：

1. `consent-summary.json` 的 included/placeholder 數量。
2. `redaction-log.json` 只有 category/action/count，沒有被移除的值。
3. `review-checklist.md` 每項均由人工審查，特別注意數學圖片、小班組合、地點、自由文本與間接識別線索。
4. Included attachment metadata 仍需獨立判斷；此 pipeline 不複製 attachment binary。

只有自動處理與人工 review 都通過後，才能把 sanitized package 送到下一個已授權的本機步驟。

## D. Import dry-run

```sh
python -m tools.sheets_importer \
  exports/C01-7K4M2Q-0702-1000/metadata.json \
  local-data/sanitized/C01-7K4M2Q-0702-1000/sanitized-thread.json \
  --adapter dry-run \
  --batch-size 100
```

比對 stdout 中每一列的 destination、idempotency key 與 values，確認無 raw/internal/Discord IDs、attachment filenames/URLs/bytes。`dry-run` 不寫檔也不連網。

如要測試本機持久化與 rerun deduplication：

```sh
python -m tools.sheets_importer \
  exports/C01-7K4M2Q-0702-1000/metadata.json \
  local-data/sanitized/C01-7K4M2Q-0702-1000/sanitized-thread.json \
  --adapter csv \
  --csv-dir local-data/sheets-import-demo
```

對同一輸入再執行一次，不應新增重複 rows。`mock` adapter 用於批次/retry/partial-failure tests。`sheets` adapter 目前固定 `NOT_CONFIGURED` 且不發 request。`clasp` 只管 GAS source，不是資料上傳工具。

## 失敗與停止

- **Selection/permission 失敗**：停止，不改用更寬鬆的 query 或整 server export。
- **Private Support / case-level EXCLUDED**：保持 deny，不覆寫 policy。
- **Manifest/hash/schema 失敗**：封鎖該 package 並重新 full dump，不手動修正成「看起來可用」。
- **Residual PII 疑慮**：停止 import/AI handoff，交由資料 owner 重新判定。
- **Partial import failure**：保留成功 rows 與失敗報告；只重試 adapter 明確標示 retryable 的 rows，不重送全批。
- **發現不當外洩**：停止、移離 artifact、保留 metadata-only incident record，不把內容複製到 chat/issue。
