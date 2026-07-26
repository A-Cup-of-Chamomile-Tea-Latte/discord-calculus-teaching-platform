# TASK-15 report — local clasp-compatible Apps Script scaffold

## Outcome

Complete。`apps/gas` 已有可在無 Google credentials 下 typecheck/test/build 的 clasp-compatible TypeScript scaffold、`doGet`/`doPost` routers、response/config wrappers、fixture mode、placeholder clasp config 與 future deployment runbook。

## Summary

- 建立 `src/index.ts` entry，esbuild bundle 後在 `dist/Code.js` 暴露 Apps Script 需要的全域 `doGet` / `doPost`。
- 純 router 提供 `GET /`、`GET /health`、fixture-only `POST /api/fixture/echo` 與 structured 404；fixture echo只回報 key names，不保存或回傳 values。
- JSON/HTML response helper 將純 `RouteResponse` 轉為 GAS `ContentService` / `HtmlService` output。
- Script Properties configuration wrapper安全預設 `FIXTURE_MODE=true`；切到非 fixture 前要求 `SPREADSHEET_ID`。
- Cloud globals只出現在 runtime adapter/config wrapper；router與 config validation可用 fake reader完成本機 pure tests。
- `appsscript.json` 使用 V8、Asia/Taipei 且 webapp access安全預設 `MYSELF`。
- `.clasp.json.example` 只有 placeholder，root `.gitignore` 排除真實 `.clasp.json` 與 deployment state。
- Runbook 指定 future intended owner/deployer 為 `ntusupercool@gmail.com`，並明列所有尚需授權的 login/create/push/deploy steps。
- README 與 health route 都明確說明 GAS 不是 Discord Gateway host。

## Files changed

- `apps/gas/package.json`、root `package-lock.json`：GAS build/test scripts與明確宣告 esbuild 0.28.1、Vitest 4.1.10。
- `apps/gas/tsconfig.json`：strict TypeScript + Vitest types。
- `apps/gas/appsscript.json`：V8 manifest與安全 access default。
- `apps/gas/.clasp.json.example`：無真實 script ID 的 clasp template。
- `apps/gas/.env.example`：只作 local documentation，標示 runtime實際讀 Script Properties。
- `apps/gas/scripts/build.mjs`：bundle、manifest copy與 doGet/doPost/no-clasp-state verification。
- `apps/gas/src/gas-globals.d.ts`：最小 GAS runtime type boundary。
- `apps/gas/src/contracts.ts`：request/response/config/property-reader contracts。
- `apps/gas/src/config.ts`：pure + runtime Script Properties wrapper。
- `apps/gas/src/router.ts`：pure fixture router。
- `apps/gas/src/responses.ts`：GAS JSON/HTML output adapter。
- `apps/gas/src/index.ts`：doGet/doPost runtime entry與safe error envelope。
- `apps/gas/src/config.test.ts`、`router.test.ts`：8 local tests。
- `apps/gas/README.md`：local commands、routes、config與Gateway non-goal。
- `apps/gas/docs/DEPLOYMENT_RUNBOOK.md`：future manual ownership、preconditions、steps、rollback。
- `docs/reports/TASK-15-REPORT.md`：本報告。

## Commands executed

- `npm view esbuild version`、`npm view vitest version`（read-only registry version check）。
- `npm install -D esbuild@0.28.1 vitest@4.1.10 --workspace @calculus/gas`。
- `npx prettier --write "apps/gas/**/*.{ts,mjs,json,md}" ...`（`.env.example` 無 parser，其他檔案完成格式化）。
- `npm run typecheck --workspace @calculus/gas`。
- `npm run test --workspace @calculus/gas`。
- `npm run build --workspace @calculus/gas`。
- `env PATH=/tmp/codex-calculus-task12-venv/bin:… npm run check`。
- `rg` / `wc` read-only build-output inspection。

沒有 clasp login、Apps Script/Sheet creation、real script/deployment ID、push、deploy、email、HTTP request to GAS或 Google credential。

## Verification

- Tests：GAS Vitest 2 files / 8 tests、Portal Vitest 17 tests、Pytest 35 tests 全部 passed。
- Linters/type checks：完整 root check通過；secret scan 239 files / 0 findings；Prettier、Ruff lint/format、Astro 39 files 0 issues、GAS strict `tsc --noEmit`、mypy（9 source files）全部 passed。
- Builds：esbuild成功產生 `dist/Code.js`（5,654 bytes）與 `dist/appsscript.json`（194 bytes）；全域 `doGet`/`doPost`存在。
- Manual checks：build output沒有 script ID/placeholder/credential pattern；manifest、fixture mode、`MYSELF` default、Gateway non-goal與 owner runbook逐項檢查。

## Diagnostics

- GAS `ContentService` 沒有一般 server framework的任意 HTTP status control；JSON response以 `status` envelope表達 application status，consumer不可只依賴 HTTP 200。
- esbuild IIFE透過 footer建立真正 top-level `var doGet`/`var doPost`，避免 ES module syntax不相容 Apps Script。
- 初次 build發現 Node API 名稱誤寫為 `cpFileSync`；已修正為 `copyFileSync`，重跑成功。
- `dist/`被 gitignore，local build artifact不會成為 source of truth；clasp future rootDir仍指向 reproducible `dist`。

## Assumptions made

- V8、Asia/Taipei與 `executeAs=USER_DEPLOYING` 是可逆 scaffold defaults；正式 access policy尚未核准。
- `MYSELF` 是最安全的 webapp scaffold access；公開或 domain access必須另行 security/privacy review。
- Runtime property key先採 `APP_ENVIRONMENT`、`FIXTURE_MODE`、`SPREADSHEET_ID`；Tasks 16–19可在集中 wrapper擴充。
- Intended owner/deployer依 Batch C指示記為 `ntusupercool@gmail.com`，但沒有驗證或登入該帳號。

## Risks and blockers

- 高度：正式 `doPost` 必須加入 authentication、replay protection、rate limit、schema validation與 logging redaction；目前 fixture echo不能直接改成 production write endpoint。
- 高度：manifest access/execute-as 尚未完成 threat model；不可直接 deploy。
- 中度：Apps Script quota、concurrency與 response status限制使它不適合 Discord Gateway或高頻 message storage。
- 中度：GAS runtime types是最小 local declarations；若後續大量使用 Google APIs，可改用官方 type package但應避免把 cloud globals滲入 pure core。
- 無阻擋 Task 16 的問題。

## Questions for ChatGPT discussion

- 正式 web app應要求 domain-only、signed server-to-server request，還是其他 authentication？
- Apps Script execute-as與 Sheet owner角色如何分離，誰能修改 Script Properties？
- 是否採 immutable Action/build artifact與 clasp version pinning policy？

## Recommended next action

執行 Task 16：定義 Sheets tabs/columns/indexes、建立 idempotent local schema bootstrap與 in-memory repository tests；只使用 fixtures，不建立或修改真實 Sheet。

## Copy-paste handoff

Task 15 已完成 local clasp-compatible GAS scaffold：TypeScript source在 `apps/gas/src`，esbuild產生 `dist/Code.js`與manifest並暴露全域 `doGet`/`doPost`；有HTML/JSON response helpers、Script Properties config wrapper、安全預設fixture mode、health/fixture echo/404 routers、`.clasp.json.example`與deployment runbook。GAS Vitest 8/8、Portal Vitest 17/17、Pytest 35/35，完整 root check通過（secret scan 239 files/0 findings，Prettier/Ruff/Astro/tsc/mypy全過）；bundle 5,654 bytes且無script ID/credential pattern。Manifest access預設`MYSELF`；runbook指定future owner/deployer `ntusupercool@gmail.com`。README與health皆明確說明GAS不是Discord Gateway host。沒有login、cloud project/Sheet、push、deploy或寄信。正式前仍需 authentication/replay/rate limit、access policy與quota review。建議下一步Task 16 Sheets schema bootstrap。
