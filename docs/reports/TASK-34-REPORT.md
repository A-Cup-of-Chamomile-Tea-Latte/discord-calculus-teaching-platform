# TASK-34 report — next safe foundation package

## Outcome

Complete for the explicitly authorized fixture/local scope. The 2026-07-23 discussion package was preserved and implemented without connecting to Discord, Google, email, OAuth, an LLM, hosting, or real student data. Fixture/local review remains **GO**; production and real data remain **NO-GO**.

## Summary

- Preserved and read all seven files from `Discord_Project_Next_Discussion_and_Codex_Package.zip`; the incoming archive passed `unzip -t` and has SHA-256 `784c64d494acd8ad8ff5adee0f17902dd7bf6c6270f9f564ecadd6fd0dca471e`.
- Promoted only the explicitly accepted product decisions and left identity, roles, Private Support implementation, authenticated transport, retention, consent withdrawal, ownership, and live-service choices open.
- Added cryptographically random, non-PII-derived `Cxx-token-MMDD-HHMM[-P]` case numbers with strict calendar/time parsing, masking, bounded collision retry, and protected UUID mapping.
- Added the reduced desktop case projection, timeline, teaching/student activity times, attachment markers, Discord deep link, configurable manual/temporary/automatic close and reopen behavior, and a fixture-only `VERIFIED_VIEW` port.
- Required an explicit unselected AI Yes/No choice. Database state is authoritative; OP No excludes the case and OP Yes preserves per-author filtering.
- Separated working/archive contracts and fixture examples; added changed-case batches, cache/schedule/weekly rollover/archive/quota mocks.
- Made `dump_bot` the canonical reader name while retaining `archive_reader` as a compatibility package; added fixture-only structure inventory, selected dump/follow, reconciliation, manifest, and no-polling checks.
- Added synthetic student/TA/teacher/webhook actors with explicit warnings that they do not replace human OAuth, DM, UI, or permission tests.
- Added strict fixture-only Discord provisioning parse/validate/diff/print/rollback planning with exact resource shapes, recursive secret rejection, and a least-privilege bot permission allowlist.
- Added deterministic handoff packaging which retains `fixtures/exports/export-manifests.json`, distinguishes fixture exports from operator output, excludes secrets/dependencies/caches/builds/old archives/symlinks, atomically replaces output, and reports SHA-256.

## Files changed

The main new or materially extended areas are:

- `CODEX_TASKS/34_NEXT_SAFE_FOUNDATION_PACKAGE.md`, task manifest/matrix, preserved exchange package directory, accepted decision record, unresolved register, status/next-step/security documents.
- `tools/case_id/`, `case-id-mapping.schema.json`, Case/common contracts, examples, fixtures, and tests.
- `apps/portal/src/lib/` projection/lifecycle/verified-view/AI logic; reduced case page/search/form components and desktop review documentation.
- `contracts/schemas/` working/archive/projection/structure contracts plus valid/invalid examples and instance validation.
- `bots/dump_bot/`, synthetic actors, `archive_reader` migration note/compatibility imports, reader tests and documentation.
- `apps/gas/src/sheets/working-archive-spike.ts`, case ID validators/fixtures/tests, and fixture-spike documentation.
- `tools/discord_provisioning/` and tests.
- `tools/packaging/` and packaging regression tests.

Detailed component file lists are in `apps/portal/docs/DESKTOP_REVIEW_MODE.md`, `docs/reports/NEXT-SAFE-WORK-PACKAGE-07-11-REPORT.md`, and the relevant tool/package READMEs.

## Commands executed

Material local commands included directed pytest/Vitest/Ruff/mypy/TypeScript/Astro runs, root `npm run check`, the project-base Portal/GAS build, static dist and Pages workflow verifiers, deterministic package builds, `unzip -t`, archive inventory checks, SHA-256, and a fresh-extraction source gate.

The fresh-extraction gate reuses the already verified local `node_modules` and `.venv` through temporary symlinks. It does not download dependencies or claim a clean dependency reinstall; the extracted source, package inventory, tests, type checks, builds, and base-path output are the objects under test.

No commit, stage, push, remote creation, workflow dispatch, deploy, Discord/Gateway/REST call, Google API/GAS/Spreadsheet call, email, OAuth, browser-held secret, LLM call, purchase, or real-data operation was executed.

## Verification

- Root quality gate: passed.
- Secrets: 455 candidate files / 0 findings in the final pre-package-rebuild scan.
- Formatting/lint: Prettier passed; Ruff format/check passed for 87 Python source files.
- Types: Astro 48 files / 0 errors, warnings, or hints; GAS TypeScript passed; strict mypy 87 source files / 0 issues.
- Tests: Portal 43/43; GAS 48/48; Python 155/155. Python emitted only the two existing discord.py/Python 3.14 deprecation warnings.
- Build: Portal 14 static pages; 188 base-safe references and targets for `/discord-calculus-teaching-platform/`; Pages manual-deploy gate verifier passed. GAS produced its local bundle and manifest.
- Contracts: 24 Draft 2020-12 schemas plus valid/invalid instance validation.
- Packaging regression: required fixture export manifest included; fixture directories retained; operator data/dependencies/cache/build/secret/archive/symlink paths excluded; deterministic repeated builds are byte-identical.
- Fresh extraction: archive integrity, required/forbidden inventory, root checks, project-base build, Portal dist verifier, and GAS bundle are verified before handoff.

## Diagnostics

- The desktop app's managed writable root still pointed to the pre-relocation path, which no longer existed. Work was therefore performed in a complete controlled copy at `/Users/chamomiletea/Documents/Discord 微積分模組教學優化專案`, tested there, and then synchronized back to the canonical underscored project path. Active documentation continues to name only the canonical path.
- Git remains an unborn `main` with no commits or remotes. This task does not infer authorization to create either.
- The product Case token has roughly 30 bits of randomness and exposes creation month/day/time by design. It is an opaque locator, not a production authentication factor; authenticated lookup and rate limiting remain mandatory.
- Fixture/synthetic/plan tests cannot prove live Discord permission overwrites, message-content behavior, OAuth/DM/UI flows, GAS quotas, Sheets ACL/locking, trigger timing, or provider behavior.

## Assumptions made

- `Asia/Taipei` is the display timestamp zone for the case-number fragment.
- `C99` is reserved for non-standard classes/special identities; class codes remain two digits.
- Private Support receives a protected `-P` number but stays outside general lookup/export and the number grants no access.
- The non-ambiguous token alphabet excludes `0`, `O`, `1`, and `I`.
- `dump_bot` is the canonical product name; old Python symbols/config names remain a temporary compatibility layer rather than a second bot.
- The 3-day temporary and 7-day automatic closure thresholds are configurable defaults, not hard-coded policy; an unverified page view is never treated as read.

## Risks and blockers

- **High:** case lookup still lacks a production authenticated backend, anti-enumeration controls, and rate limiting. Do not use the case number as the only credential.
- **High:** Private Support mechanism/ACL, retention/deletion/backup, consent snapshots/withdrawal, and named privacy/security/data/system owners remain unresolved.
- **High:** Discord/GAS/Sheets adapters, real permissions, quotas, durable outbox/checkpoint/locking, incident kill switches, and live rollback evidence are absent.
- **Medium:** auto-close depends on a future approved verified-read signal; until then it must remain a preview/fixture behavior.
- **Medium:** synthetic actors and structure/provisioning fixtures may miss real Discord UI and role-hierarchy behavior; human review is mandatory before any apply adapter exists.
- **Medium:** the first Git baseline and treatment of exchange ZIPs still require human approval and binary/malware review.

## Questions for ChatGPT discussion

1. What authenticated backend/session model will enforce the accepted one-case-at-a-time lookup boundary?
2. Who are the named privacy, security, data, and system owners, and what retention/withdrawal rules do they approve?
3. Which minimal roles/channels/forums and Private Support mechanism should be approved before generating any non-dry provisioning adapter?
4. What event may legitimately produce `VERIFIED_VIEW`, and should automatic closure remain disabled until that evidence exists?
5. May exchange ZIPs enter the first Git baseline, or must they remain local-only artifacts?

## Recommended next action

Pause feature development. Review the accepted decisions, `docs/IMPLEMENTATION_STATUS.md`, and P0 items in `docs/NEXT_STEPS.md`; appoint owners and approve access/data-lifecycle/Private Support/Git-baseline decisions. Only then consider the already bounded, single-thread, read-only `dump_bot` test-guild spike.

## Copy-paste handoff

Task 34 已完成 2026-07-23 safe foundation package 的 fixture/local 實作：新案號 `Cxx-token-MMDD-HHMM[-P]`（安全亂數、不由個資衍生、strict calendar/time、mask、collision retry、UUID mapping）；Portal reduced desktop screen、timeline、附件marker、Last Update/Response/Read/Sync、可設定3/7日manual/temp-auto/auto close與reopen、VERIFIED_VIEW介面；AI逐案強制Yes/No且無預選，database為source of truth、OP No整案排除、OP Yes保留作者層級filter；Working/Archive schemas/examples、changed queue、GAS batch/cache/schedule/weekly rollover/quota mock；canonical dump_bot＋archive_reader compatibility、fixture structure inventory/dump/follow/reconciliation/manifest/no polling；synthetic actors；strict provisioning dry-run；deterministic packaging並回歸保護fixtures/exports/export-manifests.json及contract manifest examples。完整root gate：secret 455/0、Portal 43/43、GAS 48/48、Python 155/155（只有2個既有discord.py/Python3.14 warnings）、Astro 48 files 0 diagnostics、mypy 87 files、Ruff/Prettier/TS通過；Portal 14 pages/188 base-safe refs、GAS bundle、24 schemas。未連真實Discord/Google/email/OAuth/LLM，未部署、未用token或真實學生資料，Git仍unborn main/0 commits/0 remotes。fixture/local review GO；production/real data NO-GO。主要blockers仍是authenticated one-case backend/rate limit、Private Support ACL、retention/consent withdrawal/owners、Discord/GAS/Sheets live permissions/quota/durable storage與Git/archive基線審查。
