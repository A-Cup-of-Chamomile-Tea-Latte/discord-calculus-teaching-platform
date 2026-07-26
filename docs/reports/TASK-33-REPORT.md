# TASK-33 report — final diagnostic and ChatGPT handoff

## Outcome

Complete for the fixture/local prototype; production remains blocked by explicit governance and live-service gates. Full tests/lint/types/secrets/builds passed, repository/dependency/mock/TODO/docs/Git/base-path/cloud/live/export readiness were inventoried, and `docs/IMPLEMENTATION_STATUS.md` plus `docs/NEXT_STEPS.md` now distinguish implemented, mocked and not started work.

The final audit found and this task fixed three local safety/documentation defects before declaring the baseline green:

1. active canonical-path docs incorrectly used the old space-name directory; they now use the actual underscored root;
2. anonymization did not verify Task 26 manifest hashes and sanitized/import packages lacked cryptographic source binding; all manifest files are now verified, SanitizedThread carries source export/thread digest, importer rejects mixed packages, and tamper/mismatch tests pass;
3. CSV output relied on umask; it now enforces directory 0700/files 0600 and documents that dry-run stdout contains controlled sanitized content.

These are bounded correctness/security fixes, not silent changes to product architecture. Major unresolved access/storage/governance choices remain documented rather than guessed.

## Summary

- Reviewed all Tasks 02–32, Task 25A, architecture/ADR/security/docs, source/config/adapters, CI and generated outputs.
- Ran the sole final local gate after all parallel work and integrity fixes: root `npm run check`, project-base build/verifiers, GAS build and `git diff --check`.
- Inventoried repo/Git/size/dependencies/schemas/docs/TODO-stubs/mock services/credentials/deployments and active path drift.
- Independently inspected and tested both handoff ZIPs: `unzip -t` passed; in-memory text deep scan reported 0 secret-pattern findings. This is not malware/binary credential certification.
- Confirmed fixed product direction is preserved: NTU COOL authoritative, no continuous polling, no voice recording/transcription, no automatic LLM, Private Support separate/excluded, multi-bot separation and fixture-first development.
- Classified fixture demo/local review as GO and production/real student data as NO-GO.
- Prepared a final local handoff archive containing source, contracts, fixtures, task specifications, reports, environment notes and exchange Markdown. Git metadata, dependency trees, virtual environments, caches, generated build output, local exports and older ZIP archives are excluded; archive integrity and contents are verified before handoff, with its SHA-256 supplied alongside the file.

## Files changed

- `docs/IMPLEMENTATION_STATUS.md`: implemented/mocked/not-started matrix, final verification/environment inventory and production gates.
- `docs/NEXT_STEPS.md`: P0–P3 work ordered by value, risk and dependency.
- `docs/reports/TASK-33-REPORT.md`: this evidence-backed report and handoff.
- `PROJECT_DEFAULTS.md`, `README_使用方式.md`, `docs/diagnostics/ENVIRONMENT.md`, Task 25A report correction: active canonical underscored root.
- `contracts/schemas/sanitized-thread.schema.json` and valid example: source export/thread digest binding.
- `tools/anonymizer/pipeline.py`, README, tests: manifest file hash verification and tamper rejection.
- `tools/sheets_importer/importer.py`, adapters, README, tests: package binding rejection and 0700/0600 CSV output.
- Task 27/28 reports: final integrity hardening and directed counts.

Task 29–32 files are separately listed in their reports. No product deployment, remote or real-service state was changed.

## Commands executed

Material commands included:

- `npm run check` after all changes.
- `ASTRO_BASE_PATH=/discord-calculus-teaching-platform ASTRO_SITE_URL=https://example.github.io npm run build`.
- Portal `verify:dist ... /discord-calculus-teaching-platform/` and `verify:pages`; `git diff --check`.
- Directed Ruff/mypy/pytest for export integrity and integration (39/39).
- `git rev-parse/status/rev-list/remote`; `find`; `du`; active-path and TODO/FIXME/HACK/XXX `rg` inventories.
- `npm ls --depth=0 --workspaces`; Python package version inventory.
- Secret scan, contract/quality tests, `unzip -t` and bounded read-only archive text scanning during independent audit.

No commit/push/remote creation, GitHub workflow dispatch, Pages upload/deploy, `clasp` login/push/deploy, Apps Script/Spreadsheet creation, Discord/OAuth/email/LLM/API call, production credential, real student data or external message was used.

## Verification

- Root final gate: `npm run check` passed.
- Secrets: final post-package scan 379 candidate files / 0 findings (the complete root gate immediately before adding the three final status/report documents was 375/0).
- Formatting/lint: Prettier passed; Ruff format 68 files and lint passed.
- Types: Astro 41 files / 0 errors / 0 warnings / 0 hints; GAS TypeScript passed; strict mypy 68 source files / 0 issues.
- Tests: Portal 25/25; GAS 44/44; Python 115/115. Python has two existing discord.py 2.7.1 / Python 3.14 `asyncio.iscoroutinefunction` deprecation warnings, 0 failures.
- Python details: contracts 25, integration 1, repository quality 4, anonymizer 6, exporter 7, importer 7, plus 65 bot/common/fixture/toolchain tests.
- Builds: Portal 14 static pages; all 184 local `href`/`src`/`action` references base-safe and targets present for `/discord-calculus-teaching-platform/`; Pages manual gate verifier passed. GAS produced `dist/Code.js` and `dist/appsscript.json`.
- Contracts: 15 valid Draft 2020-12 schemas.
- Integrity: anonymizer/importer/tamper/package-binding directed suite included in 39/39 passed; Task 32 full fixture journey 1/1 passed.
- Static diagnostics: active docs contain 0 stale old-space canonical paths; active application/docs inventory contains 0 literal TODO/FIXME/HACK/XXX; no root `.env`, real `.clasp.json`, `exports/` or `local-data/` directory; no nested `.git`.
- ZIP audit: two exchange ZIPs passed integrity and bounded text deep scan with 0 secret-pattern findings; binary/malware/manual approval remains outstanding.

## Repository and dependency inventory

- Canonical root: `/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案`.
- Git: unborn `main`, 0 commits, 0 remotes; all project paths untracked. This is original state, not lost history.
- Size/count: 387 MB, 18,151 files, 28 symlinks. `node_modules` 227 MB, `.venv` 141 MB, `.mypy_cache` 13 MB; tracked-intent source/docs/config is small relative to generated dependencies.
- Runtime: Node 24.13.0, npm 11.6.2, Python 3.14.6.
- Core versions: Astro 7.1.1, TypeScript 5.9.3, Vitest 4.1.10, discord.py 2.7.1, jsonschema 4.26.0, pytest 9.1.1, mypy 1.20.2, Ruff 0.15.22.
- Node has `package-lock.json`; Python has constrained ranges but no hash lock. Local `npm ls` reports five extraneous WASM packages; use `npm ci` for a clean environment. GitHub Actions use movable major action tags, not commit SHAs. No network vulnerability audit was performed.

## Mocked-service and readiness diagnostics

### Portal / GitHub Pages

Static/base-path readiness is green, but U-011 is a production blocker: GitHub Pages cannot enforce course membership and fixture builds pre-generate case pages/list. Production must keep Pages as a no-case-data public shell with authenticated backend lookup, or use hosting that enforces course-only access.

### Apps Script / Sheets

Only local scaffold/schema/bootstrap and fixture/in-memory domain services are verified. Manifest remains `MYSELF`; non-fixture case API is unavailable; email/activation/provider/outbox/auth/CORS/CSRF/rate-limit/locking/quota/backup are not production wired. There is no real `.clasp.json`, deployment or Spreadsheet.

### Discord

Course Assistant and Archive Reader domain boundaries are verified with fakes. There is no live writer/reader REST provider, real command rollout, guild permission/intents evidence, durable checkpoint/sink/idempotency, manager identity provider or Private Support ACL evidence. The first real spike remains one read-only reader app/thread/dump in an isolated fictional test guild.

### Export lane

The fixture/local lane is ready: deterministic raw export, explicit follow, manifest hashes, consent filtering, pseudonymization, review artifacts, package binding and idempotent batch abstractions. Production blockers are live REST, durable archive→file handoff, fixture-only consent source, attachment-only policy, approved retention/release and authenticated batch destination. Dry-run stdout must be treated as controlled content.

## Decision drift and overdue decisions

The architecture follows fixed context, but `docs/decisions/UNRESOLVED.md` has 15 open entries. Several listed latest-decision points are already reached (U-002–U-010, U-012–U-015). The table lacks explicit status, named owner and decision evidence. Task 33 does not choose these product/institutional decisions; `docs/NEXT_STEPS.md` makes assigning owners and statuses the first action.

## Assumptions made

- Local fixture behavior and static artifacts may be called implemented; any provider permission, identity, quota or institutional policy without live evidence is called mocked/not started.
- Fixing integrity verification, package binding, local file permissions and active path documentation is within safe local correctness scope; choosing production hosting/auth/storage/retention is not.
- CI workflow validation is local only until a reviewed remote executes it.
- Exchange ZIPs stay in the local handoff package but should not automatically enter a future remote baseline.

## Risks and blockers

- **Critical production blocker:** no approved course-session/public-case access architecture. Mitigation: P0 Portal decision and authenticated one-case lookup/no real case data on public Pages.
- **High:** retention/consent/withdrawal/release/incident owners absent. Mitigation: name owners and close U-013/U-014 before real data.
- **High:** Private Support, Discord apps and GAS/Sheets permissions are unverified. Mitigation: ordered isolated gates with revoke/rollback evidence.
- **High:** Git has no reviewed baseline and archives have no malware/binary credential certification. Mitigation: approve/exclude archives, fresh scans, human review, then separately authorize commit/remote.
- **Medium:** durable transactions/outbox/reconciliation absent across provider side effects. Mitigation: Gate 5 storage design and failure drills.
- **Medium:** dependency reproducibility gaps (Python lock, movable Actions tags, local extraneous packages). Mitigation: clean environment, lock/hash review and optional SHA pinning.
- **Low:** two upstream Python 3.14 warnings. Mitigation: CI runs supported Python 3.12; monitor discord.py compatibility.

## Questions for ChatGPT discussion

1. Should GitHub Pages be restricted to a public information shell, with every real case operation moved to an authenticated backend, or should the Portal move to different hosting?
2. Who are the named privacy, security, data and system owners, and what are the approved retention/deletion/consent-withdrawal rules?
3. May `project-exchange/*.zip` enter the first remote baseline, or must they remain local-only handoff artifacts?
4. Is the approved first real-service experiment the proposed isolated, read-only Archive Reader single-thread dump?
5. Should curated analysis rows use new protected Sheets or a backend/object store, and who approves each analysis release?

## Recommended next action

Do not add more features. Review `docs/IMPLEMENTATION_STATUS.md`, then execute P0 items 1–4 in `docs/NEXT_STEPS.md`: assign owners/statuses, approve the Git/archive baseline, choose Portal access architecture, and approve data lifecycle/consent governance. Only then authorize the isolated read-only Archive Reader spike.

## Copy-paste handoff

Tasks 02–33 + Task25A 已完成 local fixture prototype，最終狀態是「fixture/local review GO，production/real data NO-GO」。完整驗證：final secret 379/0；Portal 25/25、Astro 41 files 0 diagnostics、14 pages/184 base-safe refs；GAS 44/44 + tsc/bundle；Python 115/115，mypy 68 files、Ruff/Prettier 通過，只有2個既有discord.py/Python3.14 warnings。Task32已以一個integration test跑通Portal fixture→Course Assistant→lookup/anonymous modal→Archive Reader→raw export→consent anonymization→Sheets dry-run。最終稽核發現並已修正：active canonical path統一為底線root；anonymizer現在驗全manifest hashes，sanitized contract保存source export/thread digest，importer拒絕mixed package；CSV固定0700/0600，回歸tamper/mismatch tests全過。未執行任何push/deploy/Discord/Google/email/OAuth/LLM/real data。Git仍是unborn main、0 commits、0 remotes、全檔untracked；兩個交接ZIP只通過integrity+文字deep scan，不是malware/binary-secret認證。主要production blockers：GitHub Pages無course-session gate且有fixture case list/prebuilt pages；GAS/Sheets auth/ACL/CORS/CSRF/quota/outbox未接；Discord live adapters/permissions/durable stores未驗；Private Support正式mechanism未核准；retention/consent snapshot/withdrawal/release/incident owners未定。下一步不是繼續加feature，而是先指定privacy/security/data/system owners、決定Portal access、retention/consent、審查Git/壓縮檔基線；然後才授權在獨立test guild做單thread、單次、read-only Archive Reader spike。
