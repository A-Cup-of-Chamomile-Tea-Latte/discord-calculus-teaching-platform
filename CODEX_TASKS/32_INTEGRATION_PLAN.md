# [Done] TASK-32: Create and exercise a fixture-only integration plan

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–31 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `tests/integration/`
- `docs/architecture/`
- `docs/reports/`
- `apps/`
- `bots/`
- `tools/`

You may also update `docs/reports/TASK-32-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Connect the local pieces only through fixture/mock adapters.

Demonstrate:
1. portal submits a fixture general question;
2. mock case service assigns a case number and thread mapping;
3. Course Assistant mock creates a thread representation;
4. portal searches the case;
5. Archive Reader mock fetches history on explicit request;
6. local exporter writes JSON/Markdown;
7. anonymizer creates an analysis package;
8. Sheets importer performs a dry-run.

Also demonstrate that:
- Private Support is not public;
- anonymous follow-up goes through the modal/service path;
- no polling occurs;
- no network/credential is required.

Write a production integration plan with explicit gates and rollback points, but do not deploy.

## Acceptance criteria

Acceptance criteria:
- One repeatable integration test covers the full fixture journey.
- Component boundaries use contracts/adapters rather than direct imports where inappropriate.
- Production-only steps are clearly separated.
- The report identifies the first real-service spike to perform later.

## Required completion report

Write `docs/reports/TASK-32-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
