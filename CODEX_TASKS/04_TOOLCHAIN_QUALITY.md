# [Done] TASK-04: Establish local toolchain and quality baseline

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–03 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `pyproject.toml`
- `package.json`
- `apps/`
- `bots/`
- `tools/`
- `.github/`
- `docs/architecture/`
- `docs/reports/`

You may also update `docs/reports/TASK-04-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Set up local, project-scoped development tooling.

Goals:
- Establish a Python package/test baseline for bots and tools.
- Establish a Node/TypeScript workspace baseline for Astro and Apps Script.
- Prefer project-local dependencies; do not require global installs.
- Add formatting, linting, type checking, and test commands.
- Provide a single documented command surface through npm scripts, Makefile, or another simple checked-in runner. Avoid introducing an obscure task runner.
- Add `.env.example` files with names only, no values.
- Pin or constrain versions conservatively based on the diagnostic report; do not guess unsupported versions.
- Document how to use `venv` and npm. If `uv`, pnpm, or another tool is already available, it may be supported as an optional faster path, not the only path.
- Configure secret scanning checks for committed files using lightweight local tests.
- Add a minimal CI placeholder that does not deploy anything.

Do not install Astro, discord.py, or clasp functionality yet beyond what is required to validate the workspace.

## Acceptance criteria

Acceptance criteria:
- Fresh local setup steps are documented.
- Formatting/lint/test commands have at least one smoke check.
- No global package installation is required.
- CI contains no deployment or secrets.

## Required completion report

Write `docs/reports/TASK-04-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
