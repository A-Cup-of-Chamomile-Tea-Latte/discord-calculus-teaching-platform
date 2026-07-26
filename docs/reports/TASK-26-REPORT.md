# TASK-26 report — local Discord thread export pipeline

## Outcome

Complete。已完成 fixture-first local CLI/library，可以 case number 或 thread ID 明確匯出一個 general-case thread，產生 `thread.json`、`thread.md`、`metadata.json` 與 `attachments.json`。實作 bounded pagination、deterministic ordering、explicit checkpoint resume、duplicate prevention、full-dump edit refresh、byte/mtime idempotency、checksums、owner-only file modes 與 metadata-last atomic replace。無 Discord connection、無 real credential/data、無 continuous process。

## Summary

- `python -m tools.discord_export <case-or-thread>` 只執行一次匯出；fixture mode 不會 fallback network。
- Fixture adapter 驗證 Case/CaseMessage/User/Membership contracts，同時支援 case number 與 thread ID resolution。
- 不傳 `after_message_id` 時是完整 dump，可擷取舊訊息 edit；傳入與 manifest cursor 一致的 Discord message ID 時才做 incremental merge。
- Rerun 內容一致時會驗證 manifest hashes 並不寫檔；增量模式拒絕 stale/mismatched checkpoint 與 duplicate message。
- Raw `thread.json` 保留 internal author ID、Discord message ID、timezone timestamp、edit、reply、content、source 與 attachment metadata；顯示標籤使用 course alias 或穩定 role/hash pseudonym，不使用真名。
- Message `INHERIT` 以 account default 解析為 INCLUDED/EXCLUDED，並保留 `ACCOUNT_DEFAULT`/`MESSAGE_OVERRIDE` 來源。
- Attachment index 不含 URL、不下載 file；Markdown 顯示 parent ID、parent author 與摘要，partial export 的 external parent 會明示說明。
- Private Support 沒有 public case number/Discord mapping，因此在 resolution 階段與 not-found 同樣 fail closed。
- Live adapter 只是 credential-environment-variable gated boundary；即使有 credential 也明確 fail closed，未實作 REST/network。

## Files changed

- `tools/discord_export/{__init__,__main__,models,adapters,pipeline,cli}.py`：adapter protocol、fixture/live boundaries、projection、pagination、resume、render、atomic persistence 與 CLI。
- `tools/discord_export/README.md`：CLI、outputs、resume semantics、raw/sanitized boundary 與 live limitation。
- `contracts/schemas/thread-export.schema.json`、`attachment-index.schema.json`：Task 26 輸出 contracts。
- `contracts/examples/valid/{thread-export,attachment-index}.json` 與 `contracts/examples/manifest.json`：有效範例與 contract suite registration。
- `contracts/schemas/README.md`、`contracts/COMPATIBILITY.md`：raw export 與 Task 27 consumer boundary。
- `tests/tools/test_discord_export.py`：7 個 pipeline/CLI-boundary tests。
- `tests/contract/test_json_contracts.py`：納入 14 個 schemas。
- `docs/reports/TASK-26-REPORT.md`：本報告。

## Commands executed

- `ruff format/check`、strict `mypy`、directed `pytest`、Prettier。
- 在 `/tmp/codex-task26-cli-export.brto77` 實際執行兩次 fixture CLI，驗證首次 write 與第二次 `unchanged=true`。
- `npm run check`、`npm run build`、`git diff --check`。

沒有執行 live adapter、Discord/OAuth/Gateway/REST、attachment download、email、deploy、commit 或 push。

## Verification

- Tests：Task 26 export 7/7；Task 26 + contract directed 30/30；完整 Python 96/96、Portal 25/25、GAS 44/44 passed。
- Linters/type checks：secret scan 338 candidates / 0 findings；Prettier/Ruff 通過；mypy 53 source files / 0 issues；Astro 41 files / 0 errors/warnings/hints；GAS tsc 通過。
- Builds：Portal 14 static pages；GAS `dist/Code.js` + `dist/appsscript.json` 成功。
- CLI：以 thread ID 匯出 4 messages/2 pages，cursor `423456789012345681`；以 case number rerun 回傳 0 added/unchanged=true。四檔皆為 mode 0600。
- Known warnings：完整 Python suite 仍只有既有 discord.py/Python 3.14 的 2 個 deprecation warnings。

## Diagnostics

- Incremental `after` 只能取得 checkpoint 之後的新訊息，不會看到較舊訊息之後發生的 edit；因此無 checkpoint 的 full dump 保留 edit refresh 用途。
- Metadata-last 可令 consumer 把 manifest 當 commit marker，但四個 independent file replaces 不是單一 filesystem transaction。Crash 後 rerun 會對 partial set fail closed；Task 32 若需自動 recovery，應加 staging-directory swap/journal。
- Task 26 是 raw export，仍含 internal/Discord IDs 與 EXCLUDED message content；必須先經 Task 27，不得直接送往 LLM/分析或公開。
- Attachment-only message 仍因 CaseMessage v1 non-empty body 而 fail closed，沒有偽造 placeholder。

## Assumptions made

- `after_message_id` 解釋為 Discord snowflake，並必須與既有 manifest cursor 完全一致。
- General-case manifest 的 `analysisPermission` 沿用 case-level decision；message-level 決策另逐筆解析。
- Fixture CLI 的 initiating manager 預設為 `usr_staff_example`；live mode 必須明確傳入 actor ID。
- Full dump 是 authoritative selected-thread snapshot，可更新同 message ID 的 edited content；incremental 只 append。

## Risks and blockers

- 高：raw exports 是敏感本機資料。Mitigation：root `/exports/` 已 Git-ignore、files 0600、Task 27 立即做 consent/anonymization，Task 29 定 retention/threat model。
- 高：live Discord REST、manager auth/audit、rate-limit/retry 未實作。Mitigation：現階段 fail closed，Task 32 實作與測試。
- 中：multi-file atomicity 有 crash window。Mitigation：metadata-last + hashes + partial-set refusal；Task 32 加 journal/recovery。
- 中：attachment-only contract gap。Mitigation：在 contract v2/ADR 決定 empty body 或 machine placeholder，之前 fail closed。

## Questions for ChatGPT discussion

- Attachment-only message 應在 CaseMessage v2 允許空 body，或採明確機器 placeholder？
- Production crash recovery 要用 directory swap/journal、SQLite transaction，還是 backend outbox？
- 除 explicit full dump 外，是否需要另一個 bounded edited-message reconciliation window？

## Recommended next action

執行 Task 27 anonymization and consent-filter pipeline：把 Task 26 raw export 轉成獨立 sanitized JSON/Markdown、redaction log、consent summary 與 human-review checklist，確實排除 Private Support 與 message-level EXCLUDED content，無 LLM/API call。

## Copy-paste handoff

Task 26 已完成 fixture-first local Discord export CLI/library。支援 case number/thread ID、bounded pagination、deterministic ordering、explicit Discord-message checkpoint resume、no duplicates、full-dump edit refresh、byte+mtime idempotency、temp-file atomic replace 與 metadata-last commit marker。輸出 `exports/<case>/thread.json|thread.md|metadata.json|attachments.json`，其中 thread/attachment 有新 1.0 schemas，metadata 沿用 ExportManifest，hashes 通過且 files 為 0600。保留 IDs/timezone/edit/reply/content/source/attachment metadata，author label 用 course alias 或 role/hash pseudonym；INHERIT 以 account default 解析並保留決策來源。Markdown 包含 reply author/context。Private Support resolution fail closed，attachment 無 URL/無下載。Live adapter 要求 credential env 與 actor，但尚未實作 REST、會 fail closed，無 network/continuous process。測試：Task26 7/7、Python 96/96、Portal 25/25、GAS 44/44；secret 338/0、mypy 53 files、Astro 41 files零診斷；Portal 14 pages/GAS bundle build 成功。風險：raw output 仍含 IDs 與 EXCLUDED content，不可直接分析；multi-file crash window、live REST/auth/audit 與 attachment-only policy 尚待解決。建議立即進入 Task 27 consent/anonymization pipeline。
