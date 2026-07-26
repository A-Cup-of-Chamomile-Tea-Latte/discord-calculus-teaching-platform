# [Done] TASK-16: Design Sheets schema and idempotent bootstrap

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–15 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `apps/gas/`
- `fixtures/`
- `docs/architecture/`
- `tests/`
- `docs/reports/`

You may also update `docs/reports/TASK-16-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Define and implement an idempotent spreadsheet bootstrap for prototype/admin data.

Sheets:
- Users
- Emails
- DiscordAccounts
- CourseMemberships
- Cases
- Posts
- Consents
- ActivationCodes
- Exports
- AuditLog
- Settings

For each sheet, document columns, types, primary key, indexes/lookups, sensitive fields, retention note, and source contract. Implement bootstrap/upgrade functions that create missing sheets and headers without deleting data.

Provide CSV or JSON fixture seed files and a dry-run mode. Do not create a real spreadsheet.

Explicitly document what is not stored synchronously:
- every Discord message;
- large attachments;
- bot sessions/tokens;
- OAuth tokens;
- high-frequency event logs.

## Acceptance criteria

Acceptance criteria:
- Bootstrap is repeatable and non-destructive.
- Headers map to Task 07 contracts.
- Plaintext activation codes and secrets are absent.
- Schema migration/version metadata exists.

## Required completion report

Write `docs/reports/TASK-16-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
