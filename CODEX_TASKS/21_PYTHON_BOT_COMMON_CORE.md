# [Done] TASK-21: Build shared Python bot core and fixture mode

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–20 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `bots/common/`
- `bots/*/`
- `tests/`
- `docs/reports/`

You may also update `docs/reports/TASK-21-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Implement shared Python infrastructure for the bot lane.

Include:
- typed configuration from environment;
- separate named configurations for each bot;
- structured logging with secret redaction;
- graceful startup/shutdown helpers;
- dry-run and fixture mode;
- contract model loading/validation;
- case/thread mapping repository interface;
- Discord client abstraction;
- error taxonomy;
- health information;
- test utilities and fake Discord client.

No live connection is required. The package must be importable without tokens.

## Acceptance criteria

Acceptance criteria:
- Unit tests run without network.
- Missing configuration produces actionable errors.
- Logs never print token values.
- Both future bots can reuse the core without circular imports.

## Required completion report

Write `docs/reports/TASK-21-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
