# [Done] TASK-26: Build local Discord thread export pipeline

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–25 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `tools/discord_export/`
- `bots/common/`
- `contracts/`
- `fixtures/`
- `tests/`
- `docs/reports/`

You may also update `docs/reports/TASK-26-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Build a local CLI/library that exports a selected case/thread from fixtures and later from Discord REST.

Inputs:
- case number or thread ID;
- fixture/live adapter selection;
- output directory;
- optional `after_message_id` checkpoint.

Outputs:
`exports/<case-number>/`
- `thread.json`
- `thread.md`
- `metadata.json`
- `attachments.json`

Preserve:
- message IDs;
- timestamps/timezones;
- edited timestamps;
- pseudonymous author label and role;
- content;
- reply-to relationship;
- attachment metadata;
- analysis permission;
- source;
- export checkpoint.

Implement pagination, deterministic ordering, resumability, and no duplicate messages. Live mode must require explicit credentials and remain unused in tests.

## Acceptance criteria

Acceptance criteria:
- Fixture export matches contracts.
- Re-running is idempotent.
- Incremental export adds only new messages.
- Markdown is readable and keeps reply context.
- No continuous process is introduced.

## Required completion report

Write `docs/reports/TASK-26-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
