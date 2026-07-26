# [Done] TASK-22: Build Course Assistant bot skeleton

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–21 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `bots/course_assistant/`
- `bots/common/`
- `tests/`
- `docs/reports/`

You may also update `docs/reports/TASK-22-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Build a fixture/dry-run Course Assistant skeleton using `discord.py`.

Initial surfaces:
- `/health`;
- create case/post service interface;
- set `nnmmm` nickname service interface;
- assign broad membership/class roles service interface;
- update case status/tag interface;
- button/modal registration hooks;
- Private Support creation hook;
- permission checks for staff-only actions.

Implement pure nickname generation and joining-order allocation through a repository abstraction. Do not join or modify a real server. Keep commands small and delegate to services.

## Acceptance criteria

Acceptance criteria:
- Bot starts in fixture mode without a Discord token.
- Command/service behavior is unit-tested.
- Nickname format enforces two class digits plus three order digits.
- No moderation or archive responsibilities leak into this bot.

## Required completion report

Write `docs/reports/TASK-22-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
