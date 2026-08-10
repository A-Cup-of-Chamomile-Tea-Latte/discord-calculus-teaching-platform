# GPT Web validation brief

## Purpose

This is a minimal, fixture-only review bundle for the Discord Calculus Module NAP BUILD completed on 2026-07-28.

Please independently review the included proposal, implementation, tests, and generated documentation. Do not treat the local validation results in `docs/reports/NAP_BUILD_REPORT.md` as proof by themselves; check whether the included code and tests support those claims.

This bundle is for review only. It is **not** a deployment package, does **not** authorize GO-APPLY, and must not be used to contact Discord, Google, Email, OAuth, or AI services.

## Deliberate omissions

To keep the upload small and safe, this bundle excludes:

- RTF duplicates and screenshots
- dependency directories, caches, and build output
- package lockfiles and prior ZIP archives
- historical work packages and unrelated legacy subsystems
- raw Discord messages, student names, Discord IDs, email addresses, attachments, Private Support content, and other real course data
- identity, message, case, email, Discord-account, attachment, and Private Support fixtures, even when synthetic

Only synthetic, fixture-only provisioning states are included. Portal tests that depend on the deliberately omitted identity/message/case fixtures are present for static inspection but cannot be rerun from this bundle. Historical test totals for omitted inputs or subsystems must be marked as unverified rather than assumed.

## Review questions

1. Are the four proposed YAML configurations internally consistent and aligned with their JSON Schemas?
2. Do the schema checks and custom validators cover the important cross-file invariants, privacy boundaries, lifecycle rules, and permission risks?
3. Do the Portal and Config Studio implementations accurately expose the proposed configuration while remaining local-only and fixture-only?
4. Does the Discord provisioning planner avoid live mutation and token/network use, preserve unmanaged objects, support idempotency and partial retry, and follow least privilege?
5. Are the AI opt-in, Private Support, dump/export scope, and real-data exclusions represented consistently across config, UI, documentation, and tests?
6. Which local validation claims are supported by the included code and tests, and which cannot be independently verified from this bundle?
7. Are the documented legacy lifecycle drift and P0 GO-APPLY gates complete enough to block unsafe deployment?
8. Are there any concrete defects that should block the next decision? Distinguish blockers from optional improvements.

## Requested response format

Please respond in Traditional Chinese with:

1. `Overall: PASS`, `PARTIAL`, or `FAIL`
2. Critical findings, each with severity and exact file/line evidence
3. A per-area evidence table covering config/schema, Portal, Config Studio, provisioning, privacy, tests, and documentation
4. Claims that are not independently verifiable from this minimal bundle
5. Remaining GO-APPLY blockers
6. Recommended next decision only; do not propose deployment commands or perform external actions

If no critical defect is found, say so explicitly. Do not invent facts about omitted files or private source data.
