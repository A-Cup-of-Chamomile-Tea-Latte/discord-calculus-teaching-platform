# TASK-27 report — anonymization and consent-filter pipeline

## Outcome

Complete。已建立無 network/LLM/API 的 local anonymizer，將 Task 26 raw export 轉成獨立 Git-ignored sanitized package。Private Support 與 case-level EXCLUDED 在讀取 thread 內容前即 fail closed；message raw policy 與目前 consent 必須都 INCLUDED 才保留內容，其餘以無原文/無附件的 placeholder 保留 chronology。

## Summary

- CLI：`python -m tools.anonymizer <raw-case-dir> --output-dir local-data/sanitized`。
- 輸出 `sanitized-thread.json/.md`、`redaction-log.json`、`consent-summary.json`、`review-checklist.md`，檔案 mode 0600。
- 新 `sanitized-thread.schema.json`；用 `m001...` 取代 message/Discord IDs，以 case-local `student-01`/`ta-01` 穩定 pseudonyms 取代 internal user ID、course alias 與 real-name label。
- 保留 timezone/edit/source/reply chronology；excluded message body 固定為 `[Content excluded by consent.]`，attachment 清空。
- 已知姓名/email、email pattern、URL、Discord mention 與 student-ID-like pattern改為類別 marker；attachment filename/ID 改為 local label。
- Redaction log 只記 message ref、category、action、count，不保存被刪值。Review checklist 明確要求人工 residual-PII 複核，不宣稱不可逆匿名。
- Raw/sanitized 目錄重疊會拒絕；預設使用已 Git-ignore 的 `local-data/sanitized`。

## Files changed

- `tools/anonymizer/{__init__,__main__,cli,pipeline}.py` 與 `README.md`。
- `contracts/schemas/sanitized-thread.schema.json`、valid example、manifest/schema README。
- `tests/tools/test_anonymizer.py`、contract schema count。
- `docs/reports/TASK-27-REPORT.md`。

## Commands executed

Prettier、Ruff format/check、strict mypy、directed pytest、Task 26 fixture export 後實際 anonymizer CLI、`npm run check`。沒有 LLM/API/network/Discord/Google/credentials/deploy/commit/push。

## Verification

- Tests：Task 27 最終 6/6（含 manifest tamper rejection）；integrity-directed anonymizer+importer+integration+contracts 39/39。初次完成基線 Python 102/102、Portal 25/25、GAS 44/44 passed；最終 root counts 見 Task 33。
- Linters/type checks：secret 346/0；Prettier/Ruff 通過；mypy 58 files；Astro 41 files 0 diagnostics；GAS tsc 通過。
- CLI E2E：4-message raw export 轉成 3 INCLUDED + 1 PLACEHOLDER，5 redaction events、0 residual pattern flags；reply `m004 -> m003` 仍可讀。
- Builds 沿用 Task 26 後已驗證的 Portal 14 pages/GAS bundle；Task 27 未改 app build code。

## Diagnostics

- Regex/known-value redaction 無法證明已清除所有間接識別資訊，尤其是數學圖片、地點、小班組合與自由文本。
- Raw Task 26 output 仍保留 EXCLUDED content 以便 authorized local archive；它必須與 sanitized package 存放/存取/保留政策分離。
- Consent fixture 是 point-in-time current policy；production 需要 consent snapshot/version/audit，避免無法重建當時決策。

## Assumptions made

- 最保守決策：raw EXCLUDED、current consent EXCLUDED、missing consent 任一成立就 placeholder。
- Structural placeholder 保留 time/role/source/reply，但不保留原文、attachment metadata 或 raw IDs。
- File extension/media type/size/hash 非內容本身，可在 included message 中保留；filename/ID 必須替換。

## Risks and blockers

- 高：去識別化不完全。Mitigation：強制 manager checklist；Task 29 定 data classification/review/release gate。
- 高：consent race/audit 尚無 durable snapshot。Mitigation：Task 32 定義 versioned consent fetch 與 audit/outbox。
- 中：附件內容未檢視。Mitigation：預設不複製附件 binary，清單要求單獨人工審查。

## Questions for ChatGPT discussion

- Production analysis release 是否必須雙人複核，並保存不含內容的 approval audit？
- Consent snapshot 應綁 export time、analysis time，或兩者都保存？
- Included attachment metadata 是否也應預設全部移除？

## Recommended next action

執行 Task 28 local Sheets batch importer，只匯入 export metadata 與經選擇的 sanitized structured messages/summaries，不傳 raw attachments，用 dry-run/CSV/mock adapters 驗證 idempotency、batch 與 partial failure。

## Copy-paste handoff

Task 27 已完成無 LLM/API/network 的 consent/anonymization pipeline。Private Support/case EXCLUDED 在讀 thread 前 fail closed；raw message policy 與目前 consent 必須都 INCLUDED，missing/EXCLUDED 以無原文無附件 placeholder 保留 chronology。處理前驗證 manifest 內所有 file hashes，sanitized package 保存 source export/thread digest binding。輸出 sanitized JSON/Markdown、無原值 redaction log、consent summary、human review checklist；IDs/真名/course alias 改為 case-local refs/pseudonyms，已知姓名/email、URL、mention、student-ID-like text 替換，attachment filename/ID 替換。Task27 最終 6/6，tamper rejection 通過；初次完成基線 Python 102/102、Portal 25/25、GAS 44/44。CLI E2E 得到 3 included + 1 placeholder，reply chronology 保留。不宣稱完美/不可逆匿名；仍需人工複核、consent version/audit 與 attachment 單獨政策。
