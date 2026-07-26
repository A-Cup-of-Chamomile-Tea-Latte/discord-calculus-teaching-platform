# TASK-12 report — fixture-backed public case lookup

## Outcome

Complete。首頁與案件列表均已接上離線 fixture lookup，public case 詳情、錯誤狀態、測試與手動 accessibility/mobile QA 均完成；正式 GAS、Discord 與 follow-up submission 仍依規格保留為 mock。

## Summary

- 建立可替換成 GAS 實作的 public case adapter contract，並以 fixture adapter 提供 client-safe projection。
- 首頁與 `/cases/` 提供案件編號查詢；接受無害的大小寫與空白差異，拒絕 malformed input，並清楚區分 found/not-found。
- Public case detail 顯示標題、狀態、最後更新、最新教學團隊回覆、允許公開的 conversation history、visibility、明確 refresh action、disabled Discord placeholder 與 disabled follow-up placeholder。
- Public adapter 排除 Private Support；匿名 fixture 不輸出作者身分；UI 不輸出 internal/Discord IDs。
- Client interaction 只在送出查詢時讀取本機 fixtures，沒有 polling timer。
- 以 375 × 812 px in-app browser 完成實際查詢、匿名詳情、keyboard semantics、base path、overflow 與 console QA，紀錄於 `apps/portal/docs/CASE_SEARCH_QA.md`。

## Files changed

- `apps/portal/src/lib/client-case-lookup.ts`：純函式 normalization、validation 與 public lookup result contract。
- `apps/portal/src/lib/client-case-lookup.test.ts`：found、not found、malformed、closed、anonymous、private-support 與 no-polling tests。
- `apps/portal/src/scripts/case-search.ts`：瀏覽器端一次性 fixture lookup、URL sync 與 accessible result rendering。
- `apps/portal/src/components/CaseSearch.astro`：可重用查詢表單、live region 與錯誤/空狀態。
- `apps/portal/src/pages/index.astro`：首頁加入 public case search。
- `apps/portal/src/pages/cases/index.astro`：案件列表頁加入相同 lookup interaction。
- `apps/portal/src/pages/cases/[caseNumber].astro`：完成 public detail、refresh、history、privacy labels 與 placeholders。
- `apps/portal/docs/CASE_SEARCH_QA.md`：手動 accessibility、mobile、privacy 與 base-path QA 紀錄。
- `apps/portal/package.json`、`package-lock.json`：補上 Node type dependency，讓 Astro check 能正確檢查 fixture imports/tests。
- `docs/reports/TASK-12-REPORT.md`：本任務交接報告。

## Commands executed

- `npm install --workspace @calculus/portal -D @types/node`（使用 `/tmp/codex-npm-cache-portal` cache；audit 0 vulnerabilities）
- `npm run check --workspace @calculus/portal`
- `npm run test --workspace @calculus/portal`
- `ASTRO_BASE_PATH=/portal-test npm run build --workspace @calculus/portal`
- `npm run verify:dist --workspace @calculus/portal -- /portal-test/`
- `ASTRO_BASE_PATH=/portal-test npm run preview --workspace @calculus/portal -- --host 127.0.0.1 --port 4322`
- `python3 -m venv /tmp/codex-calculus-task12-venv` 與在該暫存 venv 安裝 `.[dev]`
- `env PATH=/tmp/codex-calculus-task12-venv/bin:… npm run check`
- In-app browser：375 × 812 px 實際 fill/click/keyboard、DOM、overflow、base-link、privacy 與 console 檢查。

沒有執行 deploy、publish、remote resource creation、真實訊息／email 發送或 secret 設定。

## Verification

- Tests：Vitest 3 files、12 tests passed；Pytest 35 tests passed。JS tests 包含 found、not found、malformed、closed、anonymous、private-support 與 no-polling 行為。
- Linters/type checks：完整 root `npm run check` 通過；secret scan 217 files / 0 findings；Prettier 通過；Ruff lint/format 通過；Astro check 35 files、0 errors、0 warnings、0 hints；GAS TypeScript 與 mypy（9 source files）通過。
- Builds：Astro static build 成功產生 14 pages；使用 `/portal-test/` base path。Dist verifier 通過 10 required pages、130 base-safe links。
- Manual checks：首頁查詢三種狀態皆通過；匿名案件不含 raw identifier；首頁與詳情頁在 375 px 無水平溢位；所有站內 absolute links base-safe；console 0 warning/error。

## Diagnostics

- 系統 `python3` 沒有專案 dev tools；驗收改在 `/tmp` 隔離 venv 安裝 `pyproject.toml` 的 `.[dev]`，未污染 repository 或系統環境。
- Astro/Vite 對直接 import JSON fixture 的 client bundle 可正常 tree-shake/serialize；目前 dataset 很小，正式後端不得沿用將完整資料集打包到 public JS 的做法。
- Public case projection 目前只以 allowlisted fields 建構，與 internal fixture schema 分離，後續 GAS adapter 可實作同一 contract。
- `queueMicrotask` 只用來讀取 initial query parameter；程式沒有 `setInterval`、`setTimeout` 或其他 polling timer。
- Project-site base path 在 build、DOM links 與手動 preview 均通過。

## Assumptions made

- 一般 public case number 不需要 secret token；這是目前 ADR/default，仍可在安全審查後改為 rate limit、PIN 或登入。
- 匿名作者在 public UI 一律顯示描述性標籤，不顯示 pseudonymous internal ID。
- Task 12 的 follow-up 與 Discord link 只需可理解的 disabled placeholder；真正 submission 留給 Task 13/後端整合。
- Fixture lookup 可暫時打包進 static client，僅限離線 prototype；正式資料不應以此方式發布。

## Risks and blockers

- 高度：若正式 public dataset 被打包進 client bundle，任何欄位都可被下載。正式版本必須改用 server/GAS projection API，且只回傳 allowlisted fields。
- 中度：可枚舉 case number 可能造成 scraping。Task 29 應決定 rate limit、retention 與是否需要 PIN/login。
- 中度：Public conversation 的揭露範圍仍是產品/隱私決策；目前只顯示 fixture 中明確標記允許公開的內容。
- 低度：Browser QA 為單一 Chromium viewport；Task 30 可加入可重複的 cross-viewport automated checks。
- 無阻擋 Task 13 的問題。

## Questions for ChatGPT discussion

- 正式 public case lookup 是否維持無 token，或改採 PIN、登入、rate limit 的組合？
- Public detail 應顯示完整允許公開的 conversation，還是只顯示 teaching-team latest response？
- Closed case 的 follow-up 應完全禁止，或建立新案件並保留 reference？

## Recommended next action

執行 Task 13：用同一套 design system 建立 onboarding、一般提問與 Private Support 的 fixture-only forms，加入本機 confirmation/validation，並明確保持不送出真實資料。

## Copy-paste handoff

Task 12 已完成：Astro 首頁與 cases 頁已加入完全離線的 fixture 案件查詢，可整理大小寫/空白，處理 found、not-found、malformed、closed、anonymous 與 private-support exclusion；詳情頁顯示公開標題、狀態、更新時間、教學團隊回覆、conversation、visibility、明確 refresh，以及 disabled Discord/follow-up placeholders，沒有 polling，也不顯示 internal/Discord IDs。完整 root check 全過：Vitest 12/12、Pytest 35/35、secret scan 217 files/0 findings、Prettier/Ruff/mypy/TypeScript/Astro 均通過；`/portal-test/` static build 14 pages，dist verifier 通過 10 required pages/130 base-safe links。375 × 812 px 手動 browser QA 通過三種查詢狀態、匿名隱私、無水平溢位與 console 0 warning/error。正式 GAS/Discord/follow-up submission 仍為 mock。需討論正式 public lookup 是否加入 PIN/login/rate limit，以及 conversation 揭露範圍。建議下一步執行 Task 13 fixture-only onboarding/question forms。
