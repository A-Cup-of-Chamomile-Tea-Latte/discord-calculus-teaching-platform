# [Done] Task 34 — Next safe foundation package

## Objective

Implement the fixture-only engineering package supplied on 2026-07-23 without connecting to Discord, Google services, production hosting, secrets, or real student data.

The authoritative discussion inputs are preserved under:

`project-exchange/Discord_Project_Next_Discussion_and_Codex_Package/`

If an older document conflicts with `01_PRODUCT_DECISIONS_UPDATE.md`, the newer product decision applies. Questions explicitly left open remain open.

## Required work

1. Repair reproducible handoff packaging so fixture exports, including `fixtures/exports/export-manifests.json`, are retained; add a regression test and verify a fresh extraction.
2. Implement random, non-PII-derived case numbers in the forms `C12-7K4M2Q-0907-2007`, `C12-7K4M2Q-0907-2007-P`, and `C99-R8N6WX-0907-2007`, including parsing, validation, formatting, masking, collision retry, and internal UUID mapping.
3. Add the reduced case projection fields, timeline, Discord attachment markers, and desktop fixture review screen.
4. Implement configurable manual close, temporary automatic close, automatic close, and reopen behavior. Model `VERIFIED_VIEW` as a port/fixture only.
5. Require an explicit AI-analysis Yes/No choice; the original poster's case-level choice is authoritative, a No excludes the whole case, and a Yes preserves per-author filtering hooks.
6. Separate fixture-first working data from archive data and support changed-case projection plus weekly rollover concepts.
7. Rename the Archive Reader product surface to `dump_bot`, retaining a compatibility alias/migration note, and add fixture-only structure inventory, selected fetch, dump, follow, reconciliation, and export-manifest behavior with no continuous polling.
8. Add clearly labelled synthetic student/staff/webhook actors and thread/read/close/reopen lifecycle fixtures without claiming they replace human Discord/OAuth/permission tests.
9. Add GAS/GSheet mock spikes for changed-case batches, active-case cache, schedule simulation, weekly maintenance, rollover, archive index, idempotency, and quota-estimation hooks.
10. Add a declarative fixture-only Discord provisioning plan parser, validator, diff, printable plan, and rollback plan. It must not contact Discord or apply changes.
11. Update documentation, diagnostics, and a final Task 34 report.

## Safety constraints

- Do not create or modify live Discord roles, channels, forums, applications, or messages.
- Do not connect to historical course servers or read real messages.
- Do not use bot tokens, OAuth/email secrets, or a real `.env`.
- Do not deploy GitHub Pages or Apps Script, create Spreadsheets, send email, invoke Colab, call an LLM, or use real student data.
- Do not choose the unresolved identity, role, Private Support, production hosting, retention, or access-control policies.
- Preserve the no-recording, no-transcription, no-continuous-polling, fixture-first boundaries.

## Verification

- Root secret, format, lint, type, JavaScript, Python, contract, and integration gates pass.
- Portal and GAS builds pass under the documented project base path.
- Packaging regression confirms required fixtures are present and generated/dependency/private paths are absent.
- A freshly extracted final handoff ZIP passes its complete supported test/build gates.
- The report distinguishes local implementation from mocked interfaces and production blockers.

## Deliverables

- Local source, contracts, fixtures, tests, and documentation.
- `docs/reports/TASK-34-REPORT.md`.
- A reproducible final handoff ZIP plus SHA-256, created only after all verification succeeds.
