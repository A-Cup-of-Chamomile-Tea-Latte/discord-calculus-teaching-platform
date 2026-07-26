# [Done] TASK-11: Build the Astro portal scaffold

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–10 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `apps/portal/`
- `tests/`
- `.github/workflows/`
- `docs/reports/`

You may also update `docs/reports/TASK-11-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Create an Astro + TypeScript static site in `apps/portal`.

Requirements:
- static output;
- file-based routes matching Task 09;
- shared layout, navigation, metadata, and 404 page;
- components from Task 10;
- fixture-backed data adapter interface;
- strict TypeScript;
- basic unit/component tests where practical;
- no React/Vue/Svelte unless a specific interaction cannot reasonably be done with native browser APIs;
- no production API URL or secret;
- support a configurable GitHub Pages base path;
- Traditional Chinese interface copy.

Add local development, build, and preview documentation. Ensure the site builds without a backend.

## Acceptance criteria

Acceptance criteria:
- `npm` install/build/test commands succeed.
- The generated site is static.
- All required routes render using fixtures.
- Base-path navigation works in local preview.
- No backend secret is present in client code.

## Required completion report

Write `docs/reports/TASK-11-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
