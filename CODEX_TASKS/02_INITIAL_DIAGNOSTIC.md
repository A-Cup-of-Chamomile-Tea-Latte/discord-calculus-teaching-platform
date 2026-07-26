# [Done] TASK-02: Initial environment and repository diagnostic

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–01 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `docs/reports/`
- `docs/diagnostics/`

You may also update `docs/reports/TASK-02-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Inspect the target directory and produce a trustworthy baseline before implementation.

Work items:
- Confirm whether the project directory exists and whether it already contains files.
- Inspect Git status, branch, remotes, and ignore rules without modifying any remote.
- Record macOS architecture and versions/availability of Git, Python, pip, Node.js, npm, `clasp`, `gh`, and common editors. Do not install global tools.
- Check whether the path with spaces and Traditional Chinese characters causes any local tooling issue.
- Identify existing credentials/config files, but never print their contents. Report only filenames and whether they are tracked.
- Check whether the current directory appears to be inside another Git repository.
- Propose a safe toolchain based on what is already installed.
- Draft `docs/diagnostics/ENVIRONMENT.md`.
- Draft `docs/decisions/UNRESOLVED.md` with the currently known unresolved choices.
- Do not initialize Git or create application code in this task.

## Acceptance criteria

Acceptance criteria:
- No secrets are exposed.
- The report distinguishes installed, missing, and unverified tools.
- The report gives exact recommended next steps for Task 03.
- Only diagnostic/documentation files are created.

## Required completion report

Write `docs/reports/TASK-02-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
