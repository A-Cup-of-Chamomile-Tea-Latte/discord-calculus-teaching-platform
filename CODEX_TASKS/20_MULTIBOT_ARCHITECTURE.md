# [Done] TASK-20: Define multi-bot responsibilities and permissions

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–19 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `bots/`
- `docs/architecture/`
- `docs/decisions/`
- `docs/reports/`

You may also update `docs/reports/TASK-20-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Design the multi-bot boundary before implementation.

Bots:
- `course_assistant`: write/interactions, nickname/role operations, website-mediated posting, modal replies, case status;
- `archive_reader`: least-privilege read/fetch/export support;
- `moderation`: placeholder only;
- `common`: shared library, not a bot user.

Create:
- responsibility matrix;
- required Discord permissions/intents matrix;
- token/config separation;
- command namespace plan;
- event ownership and duplicate-processing policy;
- service interfaces;
- failure-isolation plan;
- whether the portal/GAS talks directly to Discord REST or through a later backend, clearly labeled unresolved where appropriate.

Do not create Discord applications or tokens. Do not assume that multiple programs may safely share one bot token.

## Acceptance criteria

Acceptance criteria:
- Every capability has one primary owner.
- Reader permissions do not include role/nickname management.
- Shared code does not imply shared credentials.
- A future single-bot deployment remains possible through interfaces.

## Required completion report

Write `docs/reports/TASK-20-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
