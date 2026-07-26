# Discord export

把一個明確指定的 general case / Discord thread 歷史轉成可重現的本機 JSON/Markdown。它不擷取整個 server、不自動排程、不下載附件、不匯出 Private Support 內容，也不直接送往 LLM。

## Fixture CLI

```sh
source .venv/bin/activate
python -m tools.discord_export C01-7K4M2Q-0702-1000 \
  --adapter fixture \
  --output-dir exports \
  --page-size 2
```

也可以使用 thread ID：

```sh
python -m tools.discord_export 223456789012345678 --output-dir exports
```

每次呼叫只執行一次 bounded export，產生：

```text
exports/C01-7K4M2Q-0702-1000/
├── thread.json
├── thread.md
├── metadata.json
└── attachments.json
```

`thread.json` 與 `attachments.json` 有獨立 JSON Schema；`metadata.json` 符合 `export-manifest.schema.json`。Manifest 保存三個 content files 的 SHA-256，每個 file 以 temp file + atomic replace 寫入，並最後替換 metadata。輸出檔權限為 owner read/write。

## Resume / incremental

`metadata.json` 的 `cursor` 是最後一個 Discord message ID。明確傳入同一 checkpoint 才會執行 incremental export：

```sh
python -m tools.discord_export C01-7K4M2Q-0702-1000 \
  --output-dir exports \
  --after-message-id 423456789012345681
```

若已有 export，傳入的 checkpoint 必須與 manifest 一致，避免 gap 或重複。不傳 checkpoint 時會執行完整 dump，因此可重新擷取舊訊息的 edit；內容完全一致的 rerun 不會重寫檔案。

## Author and analysis fields

- Raw export 保留 internal `authorUserId` 與 Discord message ID，供 Task 27 consent/anonymization 對照；這不是可公開或直接送去分析的 package。
- `authorLabel` 使用 course alias 或穩定的 role/hash pseudonym，不輸出 fixture display name。
- Message `INHERIT` 在匯出時以 account default 解析，並以 `analysisPermissionSource` 保留決策來源。
- Attachment 只保存 ID、檔名、media type、size 與已知 hash，不包含 CDN URL 且不下載內容。

## Live boundary

`--adapter live` 必須同時提供 `--initiated-by-user-id` 與明確 credential environment variable（預設名稱為 `ARCHIVE_READER_DISCORD_TOKEN`）。CLI 不接受 literal token argument。本階段 live REST adapter 會 fail closed，不會連線；正式 REST、rate-limit、audit 與 identity implementation 屬於另行核准的 production gate。
