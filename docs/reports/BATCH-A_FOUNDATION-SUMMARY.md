# Batch A Foundation summary

## Outcome

Batch A 完成。Tasks 02–08 皆達成驗收條件，沒有跳過或 blocked 任務，也沒有執行 remote、push、部署、寄信、正式 Discord/Google 連線或真實資料操作。

## Completed tasks

| Task | 結果 | 主要交付 |
|---|---|---|
| 02 Initial diagnostic | 完成 | macOS/Git/Python/Node/路徑／敏感檔診斷、未決事項 |
| 03 Monorepo scaffold | 完成 | 22 個必需目錄、責任 README、ignore/editor 規則、本機 Git main（無 remote） |
| 04 Toolchain quality | 完成 | npm workspaces、Python venv、format/lint/type/test/secret scan、無部署 CI |
| 05 Charter & glossary | 完成 | 繁中章程、詞彙表、提案前言草案 |
| 06 Architecture decisions | 完成 | 12 ADR、索引、Mermaid context diagram、13 元件責任表 |
| 07 Data contracts | 完成 | 11 record schemas + common、11 valid/7 invalid examples、相容性規則 |
| 08 Fixtures & mocks | 完成 | 37 records、5 adapters、資料字典、seed/reset、真實資料 guards |

## Skipped or blocked

- Skipped: 0。
- Blocked: 0。
- 保持 mock、未被誤標完成的外部能力：正式 Discord intents/modal/forum/private mechanism、GAS quotas/locking/CORS/Web App 權限、OAuth callback、email provider、GitHub Pages deployment。

## Exact verification

最後一次 foundation full check：

- `npm run check`: PASS。
- pytest: 35/35 passed，0 failed。
- Task 08 fixture tests: 10/10 passed；37/37 fixture records 通過 Task 07 schemas。
- Task 07 contract tests: 22/22 passed；12/12 schemas 符合 Draft 2020-12。
- toolchain smoke tests: 3/3 passed。
- mypy: 9 source files，0 issues。
- TypeScript: Portal/GAS 兩個 workspaces 均通過 `tsc --noEmit`。
- Ruff lint: all checks passed；Ruff format: 9 files formatted。
- Prettier: all matched files use Prettier style。
- secret scan: 171 Git candidate files，0 findings。
- npm install audit: 0 vulnerabilities（Task 04 安裝時）。
- Product builds: Batch A 依規格不安裝 Astro/discord.py/clasp 產品功能，因此無產品 build；Python editable package build/install 成功。

## Key diagnostics

- 本機為 Apple Silicon macOS 26.5；Git 2.52.0、Python 3.14.6、Node 24.13.0、npm 11.6.2。
- 空格與繁中路徑經 shell/Python/Node/npm 實測正常。
- Python 3.14 可執行目前 pytest/Ruff/mypy/jsonschema；discord.py 尚待 Task 21 實測。
- 公開瀏覽器、受控 API/bots、外部服務、管理者本機匯出分成不同信任邊界；瀏覽器沒有 bot token 路徑。
- Private Support 在 contract 層強制 `caseNumber=null`、`TEACHING_STAFF`、`EXCLUDED`，且公開 lookup schema 只能回傳 GENERAL case。
- Canonical `case_000421` 同時供 Portal、GAS、bots、tools 使用，避免各 lane 自建漂移資料。

## Assumptions and risks

- Local repository 使用 `main`，目前沒有 commits 或 remote；依指令包不自行 push 或建立遠端。
- 一般案件 prefix 暫用可設定的 `CALC-`，schema 目前採六位流水號。
- Pattern-based privacy/secret guards 需要 code review 補強，不能證明任意文字絕對不是個資。
- JSON Schema 不處理所有跨 record／時序規則；Task 08 tests 已補核心外鍵與 alias 一致性，後續 adapters 仍需交易與併發測試。

## Product and architecture questions

1. 公開 case lookup 是否需 PIN／登入，或最小欄位加 rate limit 即可？
2. Private Support technical spike 優先比較 restricted backend、private thread 或 restricted text channel？
3. Analysis consent 撤回是否影響既有匿名化輸出，及未來是否可能涉及研究用途？
4. 正式 case prefix／流水號長度、repository 名稱與 Pages base path 需在公開部署前確認。
5. Python lockfile 是否於 Task 30 加入，同時保留標準 pip/venv 路徑？

## Recommended next batch

執行 `BATCH_B_PORTAL.md`（Tasks 09–14）。Portal 可以直接使用已完成的 contracts、`case_000421` 與 CaseLookup mock，在不連外、不部署的前提下完成資訊架構、design system、Astro scaffold、case search、forms 與 project-site build 設定。

GAS、bots、export lanes 之後依 BATCH_C/D/E 分開循序處理；完成四條 lane 後才執行 Batch F review/integration。

## Copy-paste handoff

> Batch A Foundation（TASK-02～08）已全部完成，0 skipped、0 blocked。已建立環境診斷、monorepo、project-local npm/Python 品質工具鏈、繁中章程／詞彙表／提案前言、12 ADR、架構圖、11 種 JSON records + common schema、11 valid/7 invalid contract examples，以及 37 筆完全虛構 fixtures 與五種 mock adapters。最終 `npm run check` PASS：pytest 35/35、mypy 9 files 0 issues、Portal/GAS TS typecheck 通過、Ruff/Prettier 通過、secret scan 171 files 0 findings。Private Support 在 schema 層強制不公開與分析排除；四 lane 共用 `case_000421`。沒有 remote/push/deploy/email/正式 Discord/GAS 或真實資料。未決為公開查詢保護、Private Support 正式機制、consent 撤回、case prefix 與部署設定。下一步建議 BATCH_B_PORTAL（TASK-09～14）。
