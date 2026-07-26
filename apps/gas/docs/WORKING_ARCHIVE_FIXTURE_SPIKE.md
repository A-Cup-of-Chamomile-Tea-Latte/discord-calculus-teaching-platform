# Working／Archive GAS fixture spike

`src/sheets/working-archive-spike.ts` 是純 TypeScript/in-memory 行為模型：

- changed-case batch write 與 `caseId:changeVersion` idempotency；
- active-case query cache，資料變更時立即 invalidation；
- bounded trigger schedule simulation（只回傳時間，不註冊 trigger）；
- weekly maintenance dry-run plan；
- closed working row rollover 與 archive index；
- injected quota estimator hook。

`schema.ts` v1.2.0 補上 Working/Archive sheet definitions，`bootstrapWorkbook` 仍預設
dry-run 且只操作 injected workbook port。現階段沒有 `SpreadsheetApp` adapter、ScriptApp
trigger、production spreadsheet ID、Email、Colab、網路呼叫或真實學生資料。正式實作前需決定
workbook 分期、quota budget、lock/outbox、retention、restore 與 operator ownership。
