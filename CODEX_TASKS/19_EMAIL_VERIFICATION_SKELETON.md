# [Done] TASK-19: Create email verification skeleton without sending email

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–18 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `apps/gas/`
- `contracts/`
- `fixtures/`
- `tests/`
- `docs/reports/`

You may also update `docs/reports/TASK-19-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Create provider-neutral email verification logic.

Support:
- institutional email record;
- optional preferred contact email;
- six-digit or equivalent one-time code;
- hashed code storage;
- expiry;
- attempt limit;
- resend cooldown;
- successful verification timestamp;
- audit event;
- mock email provider.

Document the future Gmail/Apps Script quota implications for `ntusupercool@gmail.com` and the distinction between controlling an NTU Mail address and proving course enrollment.

Do not send real email. Do not hardcode sender identity, secrets, or HTML tracking.

## Acceptance criteria

Acceptance criteria:
- Mock flow works end to end.
- Codes expire and cannot be reused.
- Rate/attempt behavior is tested.
- The report lists exact cloud steps still required.

## Required completion report

Write `docs/reports/TASK-19-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
