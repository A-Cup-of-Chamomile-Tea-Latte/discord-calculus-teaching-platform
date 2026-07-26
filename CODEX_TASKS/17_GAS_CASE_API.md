# [Done] TASK-17: Build fixture-first GAS case lookup API

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–16 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `apps/gas/`
- `apps/portal/`
- `tests/`
- `docs/reports/`

You may also update `docs/reports/TASK-17-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Implement a fixture-first API surface for public general-case lookup.

Suggested operations:
- health;
- lookup general case by case number;
- optional explicit refresh request abstraction;
- submit follow-up placeholder;
- structured errors.

Requirements:
- no continuous polling;
- reject Private Support from public lookup;
- adapter interface for future Sheets and Discord providers;
- CORS/redirect behavior documented for a GitHub Pages client;
- request validation;
- rate-limit strategy documented, but no overbuilt infrastructure;
- audit only non-sensitive metadata;
- portal GAS adapter implemented behind the same interface as fixture adapter.

No real Discord token, Sheets ID, or deployed endpoint.

## Acceptance criteria

Acceptance criteria:
- Contract tests prove portal fixture and GAS fixture adapters return compatible data.
- Private cases are excluded.
- Client code does not receive backend secrets or internal token material.
- Local tests cover malformed and missing case numbers.

## Required completion report

Write `docs/reports/TASK-17-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
