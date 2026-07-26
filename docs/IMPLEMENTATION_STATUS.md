# Implementation status

Last verified: 2026-07-26 (Asia/Taipei)  
Canonical root: `/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案`

## Executive status

**Fixture/local review: GO. Production or real student data: NO-GO.**

Tasks 02–34 and the Task 25A relocation/hardening pass are implemented locally. Task 34 adds the accepted random Case ID format, reduced desktop projection, attachment markers, configurable closure/verified-view interfaces, explicit AI Yes/No eligibility, separated working/archive models, canonical `dump_bot`, synthetic actors, GAS maintenance mocks, strict provisioning dry-run, and reproducible packaging. The complete fixture journey, static builds, contracts, secret guards, and non-deploying CI definitions pass locally.

This is not an institutional integration or production deployment. No remote repository, commit baseline, GitHub Pages publication, Apps Script project/deployment/Spreadsheet, Discord application/guild connection, OAuth client, email delivery, Google API call, LLM call, or real student data was used.

## Implemented, mocked, and not started

| Area                  | Implemented and verified locally                                                                                                                                                                           | Mocked / fail-closed boundary                                                                              | Not started / production blocker                                                                                                      |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Portal                | Astro static portal; 14 pages; strict `Cxx-token-MMDD-HHMM[-P]` parsing; reduced fixture screen/timeline/attachments; lifecycle preview; explicit AI radio; project-base verifier                          | Submit/lookup, verified-view and lifecycle providers use fixtures; generated case pages are fictional only | Course-session auth; authenticated one-case production projection; remove real-case list/prebuild from public output                  |
| GAS / Sheets          | clasp-compatible local scaffold; 11-sheet schema/bootstrap; fixture case API; activation/email logic; changed-case batches/cache/schedule/weekly rollover/archive/quota mocks; local bundle              | In-memory repositories/providers; non-fixture cases return unavailable; deployment manifest stays `MYSELF` | Cloud project/deployment/Sheet; authenticated cross-origin transport; ACL/locks/quota/outbox; production email/activation providers   |
| Course Assistant      | Multi-bot boundaries; common config/contracts/logging/idempotency; fixture writer; membership/status; anonymous modal/service; Private Support backend-only model                                          | Discord application starts fixture-safe with only health surface; all writes use test doubles              | Live writer adapter/app commands; actual roles/permissions/intents; durable stores/outbox/audit; Private Support live mechanism       |
| `dump_bot`            | Canonical reader name; `archive_reader` compatibility alias; manager allowlist; bounded dump/follow; fixture structure inventory/reconciliation/manifest; no polling                                      | Fake Discord reader and in-memory index/checkpoint/sink/idempotency; fixture-only IDs                       | Live REST reader; durable checkpoint/handoff; manager identity provider; rate-limit/audit evidence                                    |
| Raw export            | Case/thread CLI; deterministic pagination; full/edit refresh; explicit incremental checkpoint; no duplicates; 0600 atomic four-file output; JSON contracts and hashes                                      | Live adapter requires credential then rejects without network                                              | Live Discord REST implementation; durable `dump_bot`→export transaction; attachment-only policy                                   |
| Consent/anonymization | Manifest hash verification; current consent resolution; Private/EXCLUDED fail closed; placeholders; PII category replacement; case-local pseudonyms; review artifacts; source export/thread digest binding | Consent/user/name sources are fixtures; regex redaction is intentionally imperfect                         | Durable versioned consent snapshot; withdrawal/reprocessing; approved release owner/destination; attachment-content review automation |
| Batch import          | Schema validation; package binding check; export/message/summary keys; batches; bounded row retry; partial failures; dry-run; 0700/0600 CSV; mock endpoint                                                 | Future Sheets API adapter always not configured; default curated sheet names are abstract mapping          | Authenticated endpoint; atomic idempotency/locking/audit; approved curated storage and schema migration                               |
| Provisioning          | Declarative fixture plan parser; strict shapes; least-privilege permission allowlist; recursive secret rejection; diff/print/rollback plan                                                                | Compares only against fixture server state and never applies a plan                                        | Approved role/channel/forum design; live permission matrix; human-reviewed test-guild provisioning adapter                            |
| Security/privacy      | 20-finding threat model; user DM/privacy guide; incident/fallback runbook; no-real-data/secret guards                                                                                                      | Owners are role labels, not appointed people; live evidence absent                                         | Resolve production blockers, retention, consent, access, incident ownership and kill-switch drills                                    |
| CI/testing            | 6-job read-only/non-deploying workflow; root Python suite; Portal/GAS jobs; contract/fixture/real-data guards; generated export lane                                                                       | Workflow only validated locally; no remote runner execution                                                | Create reviewed remote/baseline; optionally pin Actions by SHA; branch protection and hosted-runner evidence                          |
| Documentation         | Reviewer README; architecture/local-dev/data model/demo/operator/student/TA/fallback/deployment-not-done guides; proposal preface                                                                          | Institution-specific wording remains draft                                                                 | Professor/institution/privacy review and linguistic polishing                                                                         |
| Repository            | Canonical root fixed; `.git` preserved; no nested repo; active path docs corrected; ZIPs integrity/deep text scan evidence                                                                                 | Git is unborn `main`; all files untracked; no remote                                                       | Human-reviewed initial baseline; decision whether exchange ZIPs enter remote; Python dependency lock/hashes                           |

## Final local verification

- M3 documentation/configuration audit: `docs/README.md`, `docs/CONFIGURATION.md` and `CODEX_TASKS/README.md` now distinguish current configuration, historical task evidence and production blockers; all local Markdown targets resolve.
- Root `npm run check`: passed.
- Secret scan: 455 candidates, 0 findings in the final pre-package-rebuild gate.
- Python: 155/155 passed; two existing discord.py/Python 3.14 deprecation warnings.
- Portal: 43/43 tests; Astro 48 files with 0 errors/warnings/hints.
- GAS: 48/48 tests; TypeScript typecheck passed.
- Python type/lint/format: mypy 87 source files with 0 issues; Ruff and Prettier passed.
- Builds: Portal 14 pages; 188 project-base-safe local references; GAS `Code.js` + manifest bundle.
- Contracts: 24 Draft 2020-12 schemas plus valid/invalid instance examples.
- Integration: one complete fixture journey passed.

## Environment and repository inventory

- Node 24.13.0; npm 11.6.2; Python 3.14.6.
- Astro 7.1.1; TypeScript 5.9.3; Vitest 4.1.10; discord.py 2.7.1; jsonschema 4.26.0; pytest 9.1.1; mypy 1.20.2; Ruff 0.15.22.
- Repository working copy: approximately 399 MB and 18,254 files before the final archive. Dependencies and caches dominate size and are excluded from handoff packaging.
- Git: unborn `main`, 0 commits, 0 remotes; no nested `.git`.
- Local `npm ls` reports five extraneous WASM packages; `npm ci` on a fresh checkout is the authoritative clean install path.
- Node has a lockfile. Python uses constrained ranges but no hash-locked environment file.

## Production go/no-go gates

Production remains **NO-GO** until all high-severity blockers in `docs/security/SECURITY-PRIVACY-THREAT-MODEL.md` are closed or explicitly accepted by named owners. At minimum:

1. implement the accepted static-shell-only Pages boundary, authenticated one-case lookup, and no-real-case-prebuild verification;
2. approve retention/deletion/backup and versioned-consent withdrawal rules;
3. appoint privacy/security/data/system owners and exercise incident kill switches;
4. validate separate least-privilege Discord reader/writer apps in an isolated test guild;
5. validate authenticated backend/GAS transport, Sheet ACL/locking/quota and batch idempotency;
6. approve Private Support storage/ACL mechanism;
7. create a reviewed Git baseline without unapproved archives, credentials, or real data.

The production spike order and rollback points are in `docs/architecture/PRODUCTION_INTEGRATION_PLAN.md`.
