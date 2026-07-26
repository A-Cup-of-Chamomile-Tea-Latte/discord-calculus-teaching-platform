# TASK-16 report — Sheets schema and idempotent bootstrap

## Outcome

Complete。11個prototype/admin sheets的columns/types/PK/index/sensitive/retention/source contract已定義並文件化；non-destructive bootstrap、schema metadata upgrade、dry-run、GAS adapter、in-memory tests與JSON fixture seed全部完成，未建立或修改真實Spreadsheet。

## Summary

- 定義 `Users`、`Emails`、`DiscordAccounts`、`CourseMemberships`、`Cases`、`Posts`、`Consents`、`ActivationCodes`、`Exports`、`AuditLog`、`Settings` 11 sheets。
- Header順序與Task 07 contracts對應；contract nested arrays/objects以明確`*Json` cell欄位序列化。
- Bootstrap只做三類action：create missing sheet、append missing headers、upsert兩筆managed schema metadata；不刪除／rename／reorder既有sheet、column、row或extra header。
- `dryRun=true`只產生plan，不呼叫mutation methods；apply後第二次執行回傳0 actions。
- Settings維護`schema.version=1.0.0`與`schema.migration.last=0001-initial-prototype-schema`；舊值可更新，operator-owned settings保留。
- GAS workbook adapter集中隔離`SpreadsheetApp`；fixture mode會在`openById`前拒絕cloud bootstrap。
- Bundle公開`bootstrapSheetsDryRun`與`bootstrapSheetsApply` operator functions；apply仍需non-fixture config與明確人工動作。
- JSON seed涵蓋所有11個sheet keys，使用少量fictional Users/Cases/ActivationCodes/Settings rows；activation只含`sha256:` verifier hash。
- 文件明確排除同步儲存完整Discord messages、large attachments、bot sessions/tokens、OAuth tokens與high-frequency event logs。

## Files changed

- `apps/gas/src/sheets/schema.ts`：v1.0.0 schema catalog、columns、indexes、sensitivity、retention、source與metadata rows。
- `apps/gas/src/sheets/bootstrap.ts`：port contracts與dry-run/non-destructive bootstrap。
- `apps/gas/src/sheets/in-memory-workbook.ts`：deterministic local workbook/sheet test adapter。
- `apps/gas/src/sheets/gas-workbook.ts`：isolated SpreadsheetApp adapter與runtime operator bootstrap。
- `apps/gas/src/sheets/schema.test.ts`：15-test GAS suite中的7個schema/bootstrap tests。
- `apps/gas/src/gas-globals.d.ts`：最小Spreadsheet/Sheet/Range runtime declarations。
- `apps/gas/src/index.ts`：公開dry-run/apply operator functions。
- `apps/gas/scripts/build.mjs`：驗證operator globals存在。
- `apps/gas/fixtures/sheets-seed.json`：全sheet fixture seed manifest，無plaintext code/secret/token欄位。
- `apps/gas/docs/SHEETS_SCHEMA.md`：每個sheet完整columns/types/PK/index/sensitive/retention/source catalog與non-storage boundary。
- `apps/gas/README.md`：schema docs與operator function入口。
- `apps/gas/package.json`、`apps/gas/tsconfig.json`、root `package-lock.json`：GAS workspace明確加入Node test types並啟用。
- `docs/reports/TASK-16-REPORT.md`：本報告。

## Commands executed

- `npm install -D @types/node@26.1.1 --workspace @calculus/gas`。
- `npx prettier --write/check <Task 16 TS/JSON/Markdown files>`。
- `npm run typecheck --workspace @calculus/gas`。
- `npm run test --workspace @calculus/gas`。
- `npm run build --workspace @calculus/gas`。
- `env PATH=/tmp/codex-calculus-task12-venv/bin:… npm run check`。
- `wc`/`rg` read-only bundle/fixture inspection。

沒有Spreadsheet creation/open、Sheet mutation、clasp login/push/deploy、Google credential、real ID或network request。

## Verification

- Tests：GAS Vitest 3 files / 15 tests、Portal Vitest 17 tests、Pytest 35 tests全部passed；GAS tests涵蓋11-sheet catalog、unique headers/PK、activation no-plaintext、seed/header mapping、dry-run no mutation、apply idempotence、legacy header/row preservation與metadata-only upgrade。
- Linters/type checks：完整root check通過；secret scan 247 files / 0 findings；Prettier、Ruff lint/format、Astro 39 files 0 issues、GAS strict `tsc --noEmit`、mypy（9 source files）全部passed。
- Builds：GAS bundle成功；`dist/Code.js` 22,895 bytes、manifest 194 bytes；`bootstrapSheetsDryRun`/`Apply` globals存在。
- Manual checks：schema docs逐sheet核對；seed無`plaintextCode`/`nonce`/`secret`/`token`資料欄；bundle中相關字樣只出現在明確禁止儲存的documentation strings。

## Diagnostics

- Google Sheets沒有資料庫級secondary index；文件中的indexes/lookups是未來repository應維護的lookup策略與uniqueness checks，不代表Sheet自動constraint。
- JSON cell columns保持contract topology，但需在write/read boundary做schema validation與canonical JSON serialization。
- Header append策略可保留legacy data，但欄位rename/type conversion不能自動猜測，必須新增explicit migration ID與測試。
- `Posts`只適合curated/low-frequency case records；完整Discord history應由Task 26 explicit local export處理。

## Assumptions made

- Spreadsheet schema version與JSON contract version分開：Sheets migration使用`1.0.0`，row `schemaVersion`仍依Task 07使用`1.0`。
- Nested contract fields在Sheet以`verifiedEmailIdsJson`等suffix序列化，避免跨多欄位失去topology。
- `Settings.settingValue`被視為sensitive但永不放runtime secret；Script Properties才是runtime config boundary。
- `schema.version`與`schema.migration.last`是bootstrap唯一可更新的managed rows；其他Settings rows屬operator資料。

## Risks and blockers

- 高度：正式apply前需Sheet備份、access review、row-level validation與migration rollback；目前沒有cloud smoke test。
- 高度：Sheets access無row-level security，Private Support資料需要嚴格file sharing與可能的獨立storage決策。
- 中度：uniqueness/index由application code實作，concurrent writes需要LockService/atomic strategy（Task 17/18）。
- 中度：retention periods尚未定量；Task 29必須定義每sheet的天數、deletion與legal/audit exceptions。
- 無阻擋Task 17的問題。

## Questions for ChatGPT discussion

- Private Support是否應放同一Spreadsheet，或使用獨立受限Sheet/storage？
- 每個sheet的具體retention天數與刪除/匿名化策略為何？
- JSON cell fields的size上限、canonical serialization與migration policy如何定義？
- 是否需要額外的lookup sheets，或由repository每次建立in-memory index？

## Recommended next action

執行Task 17：在`CaseRepository` interface後建立fixture/in-memory case API、GET/POST validation、public projection與idempotent write tests；cloud adapter保持隔離且不連真實Sheet。

## Copy-paste handoff

Task 16已完成11個Sheets schema與non-destructive bootstrap：Users、Emails、DiscordAccounts、CourseMemberships、Cases、Posts、Consents、ActivationCodes、Exports、AuditLog、Settings全部有columns/types/PK/index/sensitive/retention/source contract文件。Bootstrap支援dry run，只create missing sheets、append missing headers、upsert兩筆managed schema metadata；不刪資料，apply後第二次0 actions，legacy extra headers/rows與operator settings都保留。GAS adapter在fixture mode會先拒絕openById，bundle公開dry-run/apply operator functions。JSON seed涵蓋11 sheets，activation只存`sha256:` verifier hash。完整root check全過：GAS Vitest 15/15、Portal 17/17、Pytest 35/35、secret scan 247 files/0 findings，Prettier/Ruff/Astro/tsc/mypy均成功；Code.js 22,895 bytes。沒有建立/開啟/修改真實Sheet。需決定Private Support是否獨立storage、具體retention、JSON cell policy與concurrent uniqueness/locking。建議下一步Task 17 GAS case API。
