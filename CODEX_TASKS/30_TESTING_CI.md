# [Done] TASK-30: Unify tests, builds, and non-deploying CI

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–29 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `tests/`
- `.github/workflows/`
- `apps/`
- `bots/`
- `tools/`
- `docs/reports/`

You may also update `docs/reports/TASK-30-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Create a coherent quality gate across all implemented lanes.

Include:
- contract validation;
- fixture validation;
- portal build and tests;
- GAS pure-logic tests/build;
- Python unit tests;
- formatter/linter/type checks;
- secret-pattern check;
- no-real-data fixture check;
- link/base-path check for GitHub Pages;
- generated export validation.

Create a non-deploying GitHub Actions workflow with dependency caching and separate jobs. No credentials or external service calls. Document local equivalents.

Fix straightforward defects found by the quality gate, but record architecture/product issues instead of hiding them.

## Acceptance criteria

Acceptance criteria:
- CI can run on a fresh checkout without secrets.
- Exact pass/fail counts are in the report.
- Failing checks are not disabled merely to make CI green.
- Deployment remains a separate manual future step.

## Required completion report

Write `docs/reports/TASK-30-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
