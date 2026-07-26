# TASK-17 report — fixture-first GAS public case API

## Outcome

Complete。Fixture-first GAS case service/router、provider ports、public projection、refresh/follow-up placeholders、structured validation/errors、non-sensitive audit contract與Portal GAS adapter全部完成；Portal/GAS fixture compatibility tests通過，未連真實Sheets、Discord或deployed endpoint。

## Summary

- 新增`CaseRepository`、`RefreshRequestProvider`、`FollowUpProvider`、`CaseAuditSink`與`Clock` ports，隔離future Sheets/Discord/runtime providers。
- `CaseService`實作normalize/validate、public lookup、public list、explicit refresh與follow-up placeholder。
- Public projection嚴格對齊Task 07 `CaseLookupResponse`：只含case number/type/status/visibility/public summary/updated time。
- Private Support lookup一律回`NOT_FOUND`且不在list；general `TEACHING_STAFF` case回`NOT_PUBLIC`。
- Router新增`GET /api/cases/lookup`、`GET /api/cases`、`POST /api/cases/refresh`與`POST /api/cases/follow-up`；missing/malformed/body/content皆有structured application status/error。
- Refresh是單次caller action，fixture provider回`NO_OP`/`polling:false`；沒有timer。
- Follow-up fixture不保存，回`NOT_CONFIGURED`/`persisted:false`；anonymous要求mediation flag。
- Audit sink只接受event type、outcome、route、time，不接受case number、content、user/internal ID。
- Non-fixture config未注入provider時回503，不會默默fallback到fixture data。
- Portal新增`GasCaseLookupAdapter`，實作與`FixtureCaseLookupAdapter`相同的`CaseLookupAdapter` interface，transport必須顯式注入，沒有hard-coded GAS URL。
- Portal adapter runtime allowlists response/case keys；遇到unexpected backend field直接拒絕，不傳入UI。
- `CASE_API.md`文件化GitHub Pages→GAS redirect/CORS限制、安全transport策略與未實作rate-limit plan。

## Files changed

- `apps/gas/fixtures/case-api-records.json`：與root fixtures對齊的五筆public + 一筆private minimal backend records。
- `apps/gas/src/cases/contracts.ts`：case API data/port/audit contracts。
- `apps/gas/src/cases/fixture-providers.ts`：fixture repository、refresh/follow-up、audit與clock providers。
- `apps/gas/src/cases/service.ts`、`fixture-service.ts`：pure case service與default fixture composition。
- `apps/gas/src/cases/service.test.ts`：lookup/privacy/NOT_PUBLIC/refresh/follow-up/audit/no-polling tests。
- `apps/gas/src/router.ts`、`router.test.ts`：case routes、validation/status與router tests。
- `apps/gas/docs/CASE_API.md`：operations、ports、validation、CORS/redirect、rate limit、no-polling。
- `apps/gas/README.md`：新增case API routes/docs入口。
- `apps/gas/tsconfig.json`：啟用JSON module fixture import。
- `apps/portal/src/lib/gas-case-adapter.ts`：injected-transport Portal adapter與safe projection guard。
- `apps/portal/src/lib/gas-case-adapter.test.ts`：Portal fixture/GAS fixture compatibility與backend-field rejection tests。
- `docs/reports/TASK-17-REPORT.md`：本報告。

## Commands executed

- `npx prettier --write <Task 17 GAS/Portal TS/JSON/Markdown files>`。
- `npm run typecheck --workspace @calculus/gas`。
- `npm run test --workspace @calculus/gas`。
- `npm run check --workspace @calculus/portal`。
- `npm run test --workspace @calculus/portal`。
- `npm run build --workspace @calculus/gas`。
- `env PATH=/tmp/codex-calculus-task12-venv/bin:… npm run check`。
- `rg`/`wc` read-only endpoint/polling/ID/token/bundle inspection。

沒有GAS endpoint、Sheets ID、Discord token、deployment ID、network request、cloud audit write、follow-up send或polling。

## Verification

- Tests：GAS Vitest 4 files / 26 tests、Portal Vitest 5 files / 25 tests、Pytest 35 tests全部passed；Portal中8個為GAS compatibility/guard tests。
- Linters/type checks：完整root check通過；secret scan 257 files / 0 findings；Prettier、Ruff lint/format、GAS strict tsc、Astro check 41 files 0 issues、mypy（9 source files）全部passed。
- Builds：GAS bundle成功，`dist/Code.js` 32,538 bytes。
- Manual checks：bundle/Portal adapter沒有hard-coded `script.google` endpoint、poll timer、script/deployment ID或internal token；`verifierHash`字樣只存在Task 16 backend schema catalog，不在Portal adapter/public case projection。

## Diagnostics

- Task 07 summary contract沒有title/author display/messages；Portal GAS adapter安全地把`publicSummary`當title、作者視為anonymous、messages設空。完整detail API需Task 32再定contract，不能偷偷擴充`additionalProperties:false` schema。
- GAS `ContentService`的redirect/CORS/header限制使直接GitHub Pages fetch必須在實際origin驗證；repository刻意只提供injected transport。
- GAS通常無可靠client IP，不能單靠Apps Script做完整abuse control；rate limit應優先放same-origin edge/proxy，GAS Cache/Lock只作coarse second layer。
- Fixture audit sink驗證metadata allowlist但不持久化；Task 16 AuditLog adapter未被Task 17自動啟用，避免本機任務誤寫cloud。

## Assumptions made

- Public `CaseLookupResponse`維持Task 07 schema，不在Task 17新增detail fields。
- Private Support輸入永遠表現為`NOT_FOUND`，避免確認存在；`NOT_PUBLIC`保留給well-formed general staff-only case。
- General public case list是prototype convenience；正式是否公開list需Task 29 privacy/abuse review。
- Follow-up content限制5–2000字元，fixture不保存；正式限制可在backend contract核准後調整。

## Risks and blockers

- 高度：沒有authentication、rate limiter、same-origin proxy或verified CORS；不可把future deployment URL直接接到public Portal。
- 高度：正式Sheets writes需LockService/idempotency keys與server-side schema validation，尚未實作。
- 高度：follow-up provider未實作；anonymous follow-up絕不能由user account直接發後再刪。
- 中度：public list可能增加enumeration/scraping；正式可移除list而只保留lookup。
- 中度：summary-only contract無法重現Task 12完整detail；需明確versioned contract，不可把internal messages直接公開。
- 無阻擋Task 18的問題。

## Questions for ChatGPT discussion

- 正式Portal→GAS應用same-origin proxy、signed request或其他transport/auth方案？
- Public list是否應完全移除，只允許知道case number的人查詢？
- Case detail需要哪些versioned public fields；是否顯示完整conversation？
- Lookup/refresh/follow-up各自的burst/sustained rate limits與retention為何？

## Recommended next action

執行Task 18：建立cryptographically random activation nonce、SHA-256 verifier-only storage、expiry/single-use/replay-safe pure service與concurrency port；只測fixture，不生成或保存真實activation code。

## Copy-paste handoff

Task 17已完成fixture-first GAS public case API：有CaseRepository/refresh/follow-up/audit/clock ports，lookup/list/explicit refresh/follow-up placeholder routes與request validation。Public projection嚴格對齊Task 07；Private Support一律NOT_FOUND、不進list，staff-only general case為NOT_PUBLIC；refresh無polling，follow-up不保存且anonymous標記需bot mediation；audit只記route/outcome/time。Portal新增同一CaseLookupAdapter interface的GAS adapter，transport注入、無hard-coded endpoint，unexpected backend field會拒絕。完整root check全過：GAS Vitest 26/26、Portal 25/25、Pytest 35/35、secret scan 257 files/0 findings，Prettier/Ruff/Astro/tsc/mypy均成功；Astro 41 files 0問題，GAS bundle 32,538 bytes。已文件化GAS redirect/CORS與rate-limit策略，但未實作endpoint/auth/proxy/rate limiter/Sheets或Discord provider。需決定transport/auth、是否移除public list、detail contract與quota。建議下一步Task 18 activation nonce。
