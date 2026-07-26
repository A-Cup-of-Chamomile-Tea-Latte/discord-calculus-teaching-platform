# [Done] TASK-31: Complete documentation, demo flow, and proposal preface

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–30 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `README.md`
- `docs/`
- `apps/portal/`
- `docs/reports/`

You may also update `docs/reports/TASK-31-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Prepare the repository for review by the user, a professor, or another developer.

Create/update:
- root README;
- architecture overview;
- local-development guide;
- fixture demo guide;
- deployment-not-yet-done guide;
- data model overview;
- operator workflow for dump/follow/import;
- student-facing quick guide;
- TA-facing quick guide;
- system fallback/status text;
- proposal preface and executive summary in Traditional Chinese, with an English project title;
- demo script that uses only fixtures.

Explain Astro as the framework/build system and templates as optional later visual starters. Keep the proposal practical and avoid claiming completed institutional integration.

## Acceptance criteria

Acceptance criteria:
- A reviewer can run the fixture demo from documentation.
- Platform responsibility boundaries are prominent.
- Mocked and incomplete functions are labeled.
- The proposal text is clear enough for later linguistic polishing.

## Required completion report

Write `docs/reports/TASK-31-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
