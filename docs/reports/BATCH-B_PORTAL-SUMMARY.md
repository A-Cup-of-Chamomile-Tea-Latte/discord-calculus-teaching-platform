# Batch B PORTAL summary

## Outcome

Complete。Tasks 09–14 全部完成；沒有 skipped 或 blocked local task。所有正式外部整合與 deployment 均依規格保留為 mock/manual future action。

## Completed tasks

- Task 09：information architecture、user journeys、wireframes/content states。
- Task 10：design tokens、global styles、accessible Astro component gallery 與 design-system guide。
- Task 11：Astro 7 static scaffold、14 routes、base-aware links、fixture adapter boundary、dist verifier。
- Task 12：fixture-backed public case lookup/detail、private exclusion、no polling、mobile/accessibility browser QA。
- Task 13：join、general question、Private Support fixture forms、validation 與 confirmation，no storage/network。
- Task 14：manually gated GitHub Pages project-site workflow、artifact upload、least permissions、deployment/custom-domain docs 與 dry run。

## Skipped or blocked

- Skipped：無。
- Local blockers：無。
- External items intentionally not performed：real Discord/GAS/email/file upload/private backend、remote repository、push、Pages enable/dispatch/deploy、DNS/custom domain。

## Exact verification baseline

- Portal Vitest：4 files、17 tests passed。
- Python Pytest：35 tests passed。
- Astro check：39 files，0 errors、0 warnings、0 hints。
- Root quality baseline：secret scan 226 files / 0 findings；Prettier、Ruff lint/format、GAS TypeScript、mypy（9 source files）、JS/Python tests 全部通過。
- Task 14 project-site build：14 static pages。
- Dist verifier：10 required pages、131 base-safe links，base `/discord-calculus-teaching-platform/`。
- Pages workflow verifier：manual deploy gate、least job permissions、no secrets、project-site variables 與 artifact upload 全部通過。
- Task 12 in-app browser QA：375 × 812 px，found/not-found/malformed、anonymous privacy、no horizontal overflow、base-safe links、console 0 warning/error。

## Key diagnostics

- Public fixture adapter 使用 allowlisted projection，不傳 internal/Discord IDs 或 Private Support；正式資料不能打包進 public JS。
- General case lookup目前無 token且可枚舉；rate limit/PIN/login/retention 要在 Task 29 決定。
- Form validation/confirmation 可作 UX contract，但正式 GAS/backend 必須重做 server-side validation。
- Private Support 沒有正式 protected backend；prototype 固定不公開、analysis excluded。
- Astro 所有 links/assets 已在 project-site base path dry run 通過。
- Pages workflow 不會在 push 自動 deploy；公開前仍有 manual gate 與外部設定清單。

## Product and architecture questions

- Public case lookup 是否加入 PIN/login/rate limit；conversation 公開到什麼程度？
- NTU email allowlist、`nnmmm` 指派來源與 membership authority 是什麼？
- Private Support 的 roles、retention、audit 與 incident owner 如何定義？
- Pages owner/repository/visibility/default branch、Action SHA policy 與 environment reviewer 為何？
- 何時通過 privacy review，可以公開 fixture portal？

## Recommended next batch

Batch C GAS（Tasks 15–19）。Portal 已提供清楚 adapter/form boundaries；下一步應在 `apps/gas` 建立同樣 fixture-first、完全本機的 Sheets/API/activation/email skeleton，不建立 Apps Script remote、不 deploy、不寄信。

## Copy-paste summary

Batch B Portal（Tasks 09–14）已全部完成：完成 IA/user journeys/wireframes、design system、Astro 7 static portal（14 routes）、fixture public case lookup/detail、join/general/private forms，以及 manually gated GitHub Pages workflow與部署文件。Public adapter 排除 Private Support與 internal/Discord IDs；case lookup無 polling；三種 forms只在 DOM產生 confirmation，無 browser storage/network/upload；Private Support固定不公開且排除分析。驗收基線：Vitest 17/17、Pytest 35/35、Astro check 39 files 0 問題、secret scan 226 files/0 findings且root quality全過；Task 14 project-site build 14 pages，dist verifier 10 pages/131 base-safe links，workflow verifier通過；Task 12 375px browser QA也通過。未連 Discord/GAS/email/backend，未建立 remote、push、啟用 Pages或部署。需決定 public lookup保護、email/alias規則、Private Support治理、Pages owner/repo與公開時機。建議下一批 Batch C GAS Tasks 15–19。
