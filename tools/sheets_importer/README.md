# Sheets importer

把通過驗證的本機批次資料送往管理介面。它不由 `clasp` 代替、不逐訊息同步，也不在沒有明確授權時連線正式 Sheets。

```sh
python -m tools.sheets_importer \
  exports/C01-7K4M2Q-0702-1000/metadata.json \
  local-data/sanitized/C01-7K4M2Q-0702-1000/sanitized-thread.json \
  --adapter dry-run
```

Adapters：

- `dry-run`：不寫檔/不連線，JSON stdout 完整列出 sheet、idempotency key 與每個 value。
- `csv`：寫到 Git-ignored local directory，以 `importKey` 去重，重新執行不新增 row。
- `mock`：in-memory Apps Script endpoint simulator，供 batch/retry/partial-failure tests，無 HTTP。
- `sheets`：future Google Sheets API boundary，目前一律 `NOT_CONFIGURED` 且不發送 request。

每個 export/message/summary 有獨立 idempotency key；依 destination sheet 分組、分 batch，只重試 adapter 明確標記的 retryable row，永久失敗不會丟掉同 batch 已成功資料。Destination names 可以 CLI flags 調整。

Importer 驗證 ExportManifest 與 SanitizedThread 1.0，只接受 GENERAL+INCLUDED package。Message rows不含 raw Discord/internal IDs或 attachment bytes/filenames/URLs，只有 sanitized body、pseudonym、chronology 與 attachment count。`clasp` 只管 GAS source，從不用來傳資料。

Importer 還會核對 SanitizedThread `sourceExportId` 與 `sourceThreadSha256` 是否匹配該 ExportManifest，防止把 case/export A 的 metadata 與 package B 的內容錯誤組合。CSV directory 固定 0700、files 0600。Dry-run 會顯示實際 sanitized body，因此 stdout/log 也應當作受控資料，不得貼到公開 CI log。
