# TASK-11 report — Astro static Portal scaffold

## Outcome

完成。Astro 7 strict static site、Task 09 routes、BaseLayout、404、fixture adapter、base-path helpers、Vitest 與 dist verifier 全部通過；非根 `/portal-test/` preview 首頁及案件頁均回 200。

## Summary

將 Task 10 元件掛入 Astro，建立共享 metadata/navigation/footer/skip-link layout。首頁、案件列表、五個 fixture detail、join、ask、Private Support、guide、status、component gallery 與 404 共 14 pages 可在無 backend 情況 static build。`CaseLookupAdapter` 只輸出 public projection，不輸出 internal ID、Discord snowflake 或 Private Support。

## Files changed

- `apps/portal/package.json`、root `package.json`、`package-lock.json`：Astro 7.1.1、Astro check、Vitest 4.1.10、Astro Prettier plugin、build/test scripts。
- `apps/portal/astro.config.mjs`：static output、trailing slash、可設定 base/site。
- `apps/portal/tsconfig.json`、`src/env.d.ts`：Astro strict TS 與 JSON imports。
- `apps/portal/src/layouts/BaseLayout.astro`：zh-Hant metadata、skip link、base-safe header/footer。
- `apps/portal/src/lib/{paths,case-adapter,fixture-case-adapter}.ts`：base helpers、公開 adapter contract 與 fixture projection。
- `apps/portal/src/lib/*.test.ts`：base path 及 fixture adapter Vitest。
- `apps/portal/src/pages/**`：14 個 static output pages，涵蓋所有必要 routes 與 404/gallery。
- `apps/portal/scripts/verify-dist.mjs`：required pages、zh-Hant、base-safe links、internal ID leak 檢查。
- `apps/portal/.prettierrc.json`：Astro parser plugin。
- `apps/portal/README.md`、`apps/portal/docs/DEVELOPMENT.md`：setup/dev/check/test/build/preview/base-path/manual checklist。
- `.github/workflows/ci.yml`：既有非部署 CI 加入 static portal build。
- `docs/reports/TASK-11-REPORT.md`：本報告。

## Commands executed

- `npm install ... --cache /tmp/codex-npm-cache-portal`、root `npm install`：只安裝 project-local Astro tools，audit 0 vulnerabilities。
- `npm run format`：Prettier Astro/CSS/TS/JSON 與 Ruff。
- `npm run check --workspace @calculus/portal`：Astro diagnostics。
- `npm run test --workspace @calculus/portal`：Vitest。
- `ASTRO_BASE_PATH=/portal-test npm run build --workspace @calculus/portal`：非根 static build。
- `npm run verify:dist --workspace @calculus/portal -- /portal-test/`：dist routes/links/leak verification。
- `ASTRO_BASE_PATH=/portal-test npm run preview ...` + local curl：base-path HTTP smoke。
- root `npm run check`：monorepo full verification。

## Verification

- Astro check: 31 files，0 errors、0 warnings、0 hints。
- Portal unit tests: 2 files、5/5 passed（base-path 2 + adapter 3）。
- Static build: 14/14 pages built，output=`static`，0 build errors；含 5 fixture case detail pages。
- Dist verification: 10 required page locations、128 base-safe links、0 internal fixture ID leak，base=`/portal-test/`。
- Preview smoke: `/portal-test/` HTTP 200；`/portal-test/cases/CALC-000421/` HTTP 200。
- Full checks: Python 35/35 passed；Vitest 5/5 passed；mypy 9 source files 0 issues；GAS tsc 通過；Ruff/Prettier 通過；secret scan 210 files 0 findings。
- Dependency audit: 311 packages、0 vulnerabilities。

## Diagnostics

- 使用者 npm cache 有既存 EACCES/EEXIST 問題；未刪除或強制覆寫使用者 cache，改用獨立 `/tmp/codex-npm-cache-portal` 完成安裝。
- 第一版 dist verifier 使用 URL `.pathname`，含空格／繁中路徑會保留 percent encoding 而找不到檔案；改用 `fileURLToPath()` 後通過，證明此路徑需要正確 URL→filesystem 轉換。
- 第一次 preview 未帶 `ASTRO_BASE_PATH`，依 root config 對 `/portal-test/` 回 404；以與 build 相同 base 重新啟動後兩個 smoke URLs 都回 200。文件已要求 build/preview 使用相同 base。
- Public adapter 以 sequence number 表達 reply，UI 不需要 internal message ID。

## Assumptions made

- Task 11 只建立 scaffold；case lookup 互動 states 與 forms 由 Tasks 12/13 完成。
- `ASTRO_SITE_URL` 未設定時保持 undefined，不猜 production origin；Task 14 再準備 Pages defaults。
- `components/` gallery 加 `noindex`，但仍會被 static build；正式部署前可決定是否排除。

## Risks and blockers

- 中度：Static site 的 forms/OAuth/Private Support 仍沒有受控 backend；目前所有文案清楚標 fixture/mock。
- 低度：Task 11 以 dist verifier + manual HTTP smoke 驗證 base path，尚未使用瀏覽器自動化做視覺／鍵盤 audit；Task 12/13 補 manual checklist 與 DOM tests。
- 無阻擋 Task 12 的問題。

## Questions for ChatGPT discussion

- Component gallery 正式 Pages build 是否保留但 noindex，或在 release workflow 排除？目前保留有利 visual QA。

## Recommended next action

執行 Task 12：把首頁／cases search 接上 fixture adapter 的 client interaction，加入 found/not-found/malformed/closed/anonymous/private tests、refresh action、conversation 與 follow-up placeholder，且不使用 polling。

## Copy-paste handoff

> TASK-11 已完成：使用 Astro 7.1.1 + strict TS 建立 static Portal，14 pages（首頁、案件列表、5 個 fixture detail、join/ask/private/guide/status/gallery/404）無 backend 可 build。Astro check 31 files 0 errors/warnings；Vitest 5/5；static build 14/14；dist verifier 檢查 10 required pages、128 base-safe links、0 internal ID leak；`/portal-test/` 首頁與 case preview 均 HTTP 200。全套另有 Python 35/35、mypy 0 issues、secret scan 210 files 0 findings、npm audit 0 vulnerabilities。Public adapter 不輸出 Private Support、internal IDs 或 Discord snowflake。下一步 TASK-12 fixture-backed 互動案件查詢。
