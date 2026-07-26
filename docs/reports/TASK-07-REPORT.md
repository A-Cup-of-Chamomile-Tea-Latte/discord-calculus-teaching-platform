# TASK-07 report — 共用 JSON contracts 與 enums

## Outcome

完成。11 種 record schema、共用定義、11 個有效範例、7 個有理由的無效範例、相容性規則與 contract tests 全數通過。

## Summary

採 JSON Schema Draft 2020-12 與 `schemaVersion=1.0`，定義 User、VerifiedEmail、DiscordAccount、CourseMembership、Case、CaseMessage、Consent、ActivationCode、ExportManifest、AuditEvent、CaseLookupResponse。共用 enums 固定案件狀態、類型、可見範圍、作者顯示、分析同意、來源及含時區 timestamp。Schema 以條件規則強制 Private Support 沒有公開 case number、只限 teaching staff、分析排除；公開 lookup 只能投影 GENERAL case。

## Files changed

- `contracts/schemas/common.schema.json`：版本、opaque ID、Discord ID、case number、timestamp 與共用 enums。
- `contracts/schemas/*-schema.json`／`*.schema.json`：11 種 record 的 Draft 2020-12 schemas。
- `contracts/schemas/README.md`：record 索引與 secret／ID 邊界。
- `contracts/examples/valid/*.json`：11 個完全虛構的有效最小範例。
- `contracts/examples/invalid/*.json`：7 個預期拒絕案例。
- `contracts/examples/manifest.json`：schema/instance 配對及每個 invalid case 的明確原因。
- `contracts/examples/README.md`：範例與 Task 08 fixtures 的責任區分。
- `contracts/COMPATIBILITY.md`：major/minor、enum、ID/label、投影、演進順序、時間與 secret 規則。
- `tests/contract/test_json_contracts.py`：schema 自我驗證、有效／無效範例、固定狀態、ID/label 與禁用 raw secret 欄位測試。
- `pyproject.toml`：加入 project-local `jsonschema` 與 `types-jsonschema` dev dependencies，確保 fresh setup 與 strict mypy 可重現。
- `docs/reports/TASK-07-REPORT.md`：本報告。

## Commands executed

- `.venv/bin/python -m pip install -e '.[dev]'`：將 jsonschema 4.26.0 與型別 stubs 安裝到 project-local `.venv`。
- `python -m pytest tests/contract/test_json_contracts.py -q`：單獨驗證 contracts。
- `python -m ruff format tests/contract/test_json_contracts.py`：修正一個格式差異。
- `npm run check`：完整 secret scan、format、lint、TypeScript/Python typecheck 與全部測試。

## Verification

- Contract tests: 22/22 passed——11 valid examples、7 invalid examples、4 結構／安全 invariant tests。
- Full tests: 25/25 passed，0 failed（contract 22 + toolchain 3）。
- Linters/type checks: Ruff lint 全通過；Ruff format 8 files formatted；Prettier 通過；兩個 TS workspaces 通過；mypy 8 source files、0 issues。
- Schema validation: 12/12 schemas（11 records + common）符合 Draft 2020-12。
- Secret scan: 154 candidate files、0 findings。
- Builds: editable Python package 安裝成功；本任務無產品 build。

## Diagnostics

- `jsonschema` 本身沒有內建 typing stubs；第一次完整 mypy 因此報 1 個 missing-stubs error。加入受版本限制的 `types-jsonschema` 後，完整 check 通過。
- Discord snowflake 明確以字串建模，避免 JavaScript 整數精度問題。
- CaseLookupResponse 是最小公開投影，不重用完整 Case，以結構上避免 Private Support／內部 ID 意外外洩。
- AuditEvent metadata 採 allowlist，而不是任意 object，降低偷渡 secret 或未版本化產品欄位的風險。

## Assumptions made

- `schemaVersion` 先採簡單 `1.0`；檔案 `$id` 使用不可連外的邏輯 registry URI，測試以本機 registry 解析，不發網路 request。
- case number prefix 可設定，但格式保守限制為 2–10 位大寫英數 prefix 加六位流水號；正式 prefix 仍未定案。
- Private Support 的 case number 為 `null`，而不是公開可查詢標籤；內部 `caseId` 仍存在。
- 安全預設在 record 中明寫並驗證，不依賴 validator 自動補 default。

## Risks and blockers

- 中度：Schema 驗證單筆結構，無法自行保證外鍵存在、時間先後或 CourseMembership 的 `courseAlias` 確實等於 classCode + joiningOrder；Task 08/integration adapters 需補跨 record tests。
- 中度：分析同意的撤回與歷史快照語意仍待 Task 27/29 決定；目前 contract 只分 account default 與 per-post override。
- 低度：case number 格式日後若改變，需遵循 compatibility 文件與版本遷移。
- 無阻擋 Task 08 的問題。

## Questions for ChatGPT discussion

- `caseNumber` 是否固定六位數，或應在正式 prefix 決策時一併允許不同流水號長度？
- 同意撤回應只影響未來匯出，還是要求重新處理／刪除既有匿名化輸出？

## Recommended next action

執行 Task 08：用這些 schemas 建立跨元件情境 fixtures、activation code 各狀態、混合同意訊息串，以及五種 mock adapter interfaces。

## Copy-paste handoff

> TASK-07 已完成：建立 JSON Schema Draft 2020-12 的 11 種共用 record 與 common definitions，`schemaVersion=1.0`。包含固定五種案件狀態、GENERAL/PRIVATE_SUPPORT、三種 visibility、三種作者顯示、帳號 default／逐篇 analysis permission、Discord mapping、含時區 timestamp 與四種 source。Private Support 由 schema 強制 `caseNumber=null`、`TEACHING_STAFF`、`EXCLUDED`；公開 CaseLookupResponse 只能回傳 GENERAL 最小投影。11 valid + 7 invalid examples 全部符合預期；contract tests 22/22、全套 25/25、mypy 8 files 0 issues、secret scan 154 files 0 findings。Contracts 禁止 OAuth token 與 activation-code plaintext，只保存 verifier hash。下一步 TASK-08 fixtures 與 mock adapters。
