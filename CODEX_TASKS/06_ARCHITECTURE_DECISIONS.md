# [Done] TASK-06: Create initial architecture decision records

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–05 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `docs/decisions/`
- `docs/architecture/`
- `docs/reports/`

You may also update `docs/reports/TASK-06-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Create initial ADRs, using `TEMPLATE_ADR.md`, for:
- monorepo;
- Astro static portal;
- GitHub Pages project site rather than owner site;
- Apps Script/Sheets as prototype/admin layer;
- Python + discord.py;
- multi-bot responsibility separation;
- on-demand case retrieval instead of continuous polling;
- local explicit export pipeline;
- public case-number search for general cases;
- separate protection for Private Support;
- no voice recording/transcription;
- fixture-first development.

Each ADR must include consequences and a reversal strategy. Also create an architecture context diagram in Mermaid and a component responsibility table.

Do not present proposed details as production-approved. Where Discord/GAS limitations require verification, mark them for later technical spikes.

## Acceptance criteria

Acceptance criteria:
- ADRs are individually numbered and linked from an index.
- The architecture diagram does not show direct browser access to bot tokens.
- Reversal strategies are practical.
- No hidden production dependency is introduced.

## Required completion report

Write `docs/reports/TASK-06-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
