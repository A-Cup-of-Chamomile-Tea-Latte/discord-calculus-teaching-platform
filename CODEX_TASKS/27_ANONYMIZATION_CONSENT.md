# [Done] TASK-27: Build anonymization and consent-filter pipeline

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–26 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `tools/anonymizer/`
- `contracts/`
- `fixtures/`
- `tests/`
- `docs/reports/`

You may also update `docs/reports/TASK-27-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Transform raw exports into manager-reviewed analysis packages.

Rules:
- Private Support excluded by default;
- per-message/per-post `EXCLUDE` honored;
- account default resolved deterministically;
- Discord IDs, email, student ID, real names, and attachment URLs removed or replaced;
- stable pseudonyms retained within a case;
- excluded messages may become a structural placeholder to preserve chronology;
- human review report lists possible residual PII;
- no LLM/API call is made.

Produce:
- sanitized JSON;
- sanitized Markdown;
- redaction log without the removed secret values;
- consent summary;
- review checklist.

## Acceptance criteria

Acceptance criteria:
- Tests prove excluded/private content does not appear.
- Reply chronology remains understandable.
- Redaction is conservative and documented as imperfect.
- Raw and sanitized outputs are stored separately and ignored appropriately by Git.

## Required completion report

Write `docs/reports/TASK-27-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
