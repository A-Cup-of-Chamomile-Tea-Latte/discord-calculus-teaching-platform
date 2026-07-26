# [Done] TASK-23: Build least-privilege Archive Reader skeleton

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–22 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `bots/archive_reader/`
- `bots/common/`
- `tests/`
- `docs/reports/`

You may also update `docs/reports/TASK-23-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Build a read-oriented bot/service skeleton.

Initial capabilities:
- health;
- resolve case number to thread ID;
- explicitly fetch one thread's history;
- `/dump` interface for authorized managers;
- `/follow` state model that records the last exported message ID without background polling;
- pagination abstraction;
- read-only attachment metadata;
- export handoff to local tooling.

Do not automatically mirror all messages. Do not write roles, nicknames, statuses, or normal channel messages. A fixture mode must demonstrate pagination and incremental export.

## Acceptance criteria

Acceptance criteria:
- Permission assumptions are documented and minimal.
- No timer/polling loop exists.
- `/follow` means incremental checkpointing, not continuous surveillance.
- Tests cover multiple pages and last-exported ID behavior.

## Required completion report

Write `docs/reports/TASK-23-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
