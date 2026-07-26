# Anonymizer

依同意與案件類型對明確選取的匯出資料去識別化。它不宣稱不可逆匿名，也不繞過 Private Support 的預設排除。

```sh
python -m tools.anonymizer exports/C01-7K4M2Q-0702-1000 \
  --output-dir local-data/sanitized
```

輸入必須是 Task 26 raw export directory，輸出放在分離的 Git-ignored `local-data/sanitized/<case-number>/`：

- `sanitized-thread.json` / `sanitized-thread.md`：使用案件內穩定 pseudonym 與 local message refs；
- `redaction-log.json`：只記類別、動作與數量，不記被移除的值；
- `consent-summary.json`：包含 included/placeholder 統計與決策原則；
- `review-checklist.md`：強制提醒人工 residual-PII 審查。

處理原文前會驗證 ExportManifest 列出的所有 file SHA-256。SanitizedThread 保存非敏感 `sourceExportId` 與 `sourceThreadSha256`，供後續 importer 拒絕混用不同 raw/sanitized packages；任何 checksum mismatch 都 fail closed。

只有 raw message policy 與目前 consent 都是 INCLUDED 時才保留內容。其餘訊息以 structural placeholder 保留時間與 reply chronology。自動替換已知姓名/email、email pattern、URL、Discord mention 與 student-ID-like pattern，但不宣稱完美或不可逆；送往任何分析前必須人工複核。全流程無 LLM/API/network call。
