# [Done] TASK-12: Implement fixture-backed public case lookup

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–11 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `apps/portal/`
- `fixtures/`
- `tests/`
- `docs/reports/`

You may also update `docs/reports/TASK-12-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Implement the homepage case-number search and case detail experience using the fixture adapter.

Behavior:
- normalize harmless whitespace/case differences;
- show a clear not-found state;
- display case title, status, last update, latest teaching-team response, conversation history, visibility, and a placeholder Discord link;
- provide an explicit refresh action at the interface level, but do not poll;
- show a placeholder follow-up form;
- refuse to display Private Support cases through public search;
- do not require a secret token for general cases;
- avoid leaking internal Discord IDs in the UI.

Create an adapter contract that can later be implemented by GAS. Tests should cover found, not found, malformed, closed, anonymous, and private-support cases.

## Acceptance criteria

Acceptance criteria:
- Case search works entirely offline with fixtures.
- Private Support is not rendered publicly.
- There is no polling timer.
- Accessibility and mobile behavior are tested manually and documented.

## Required completion report

Write `docs/reports/TASK-12-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
