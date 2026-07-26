# [Done] TASK-28: Build local batch import to Sheets abstraction

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–27 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `tools/sheets_importer/`
- `apps/gas/`
- `fixtures/`
- `tests/`
- `docs/reports/`

You may also update `docs/reports/TASK-28-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Build a local Python importer for structured exports and summaries.

Provide adapters for:
- dry-run;
- CSV output;
- mock Apps Script endpoint;
- future Google Sheets API.

Requirements:
- idempotency key per export/message;
- batch operations;
- schema/version validation;
- retry strategy;
- partial failure report;
- no use of `clasp` for data transfer;
- no real credentials;
- do not upload raw large attachments;
- configurable destination sheet mapping.

Create fixture demonstrations that import export metadata and selected structured messages/summaries, not a high-frequency live stream.

## Acceptance criteria

Acceptance criteria:
- Re-import does not duplicate rows.
- Failed rows are reported without losing successful rows.
- Dry-run shows exactly what would be written.
- No external API is called during tests.

## Required completion report

Write `docs/reports/TASK-28-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
