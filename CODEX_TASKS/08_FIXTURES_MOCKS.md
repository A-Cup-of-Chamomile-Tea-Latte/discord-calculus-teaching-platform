# [Done] TASK-08: Create realistic fixtures and mock adapters

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–07 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `fixtures/`
- `contracts/examples/`
- `tests/`
- `docs/reports/`

You may also update `docs/reports/TASK-08-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Create deterministic, fictional data that lets every lane work without real services.

Include:
- at least three users with invented `example.com` emails;
- two course classes;
- general cases in each status;
- one alias-authored case;
- one fully anonymous case;
- one Private Support case that is excluded from analysis;
- a message thread with replies, edits, attachment metadata, and mixed consent;
- activation codes in unused, used, expired, and revoked states;
- export manifests.

Create mock adapter interfaces or fixtures for:
- case lookup;
- Discord thread fetch;
- Sheets storage;
- email delivery;
- activation-code validation.

Fixtures must be stable and human-readable. Include a data dictionary and a test that rejects accidental `ntu.edu.tw`, real-looking phone numbers, or obvious secret patterns.

## Acceptance criteria

Acceptance criteria:
- All fixtures validate against Task 07 contracts.
- No real names, IDs, course content, or credentials appear.
- Portal, GAS, bots, and tools can consume the same case fixture.
- Fixture reset/seed instructions are documented.

## Required completion report

Write `docs/reports/TASK-08-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
