# [Done] TASK-03: Create the reversible monorepo scaffold

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–02 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `apps/`
- `bots/`
- `tools/`
- `contracts/`
- `fixtures/`
- `tests/`
- `docs/`
- `.github/`
- `README.md`
- `.gitignore`
- `.editorconfig`

You may also update `docs/reports/TASK-03-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Create the project structure without implementing product features.

Required top-level structure:
- `apps/portal`
- `apps/gas`
- `bots/common`
- `bots/course_assistant`
- `bots/archive_reader`
- `bots/moderation`
- `tools/discord_export`
- `tools/anonymizer`
- `tools/sheets_importer`
- `contracts/schemas`
- `contracts/examples`
- `fixtures/users`
- `fixtures/cases`
- `fixtures/messages`
- `fixtures/exports`
- `tests/contract`
- `tests/integration`
- `docs/architecture`
- `docs/decisions`
- `docs/reports`
- `.github/workflows`

Add a short README in each major area that defines its responsibility and non-responsibilities. Create a root README with the platform boundaries from shared context.

Initialize Git only if the directory is not already a repository and the diagnostic report says it is safe. Do not set a remote. Add a conservative `.gitignore` covering Python, Node, Astro, clasp, macOS, environment files, credentials, exports, and local data. Do not ignore fixtures or example configuration.

## Acceptance criteria

Acceptance criteria:
- The structure is coherent and empty directories are preserved using README or `.gitkeep`.
- There is no production code, token, deployment ID, or real data.
- Root documentation explains why a monorepo is used.
- Existing user files are not overwritten without preserving them.

## Required completion report

Write `docs/reports/TASK-03-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
