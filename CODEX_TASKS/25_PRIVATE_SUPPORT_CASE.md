# [Done] TASK-25: Prototype Private Support case boundary

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–24 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `bots/course_assistant/`
- `apps/portal/`
- `contracts/`
- `tests/`
- `docs/reports/`

You may also update `docs/reports/TASK-25-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Prototype Private Support without claiming production security.

Define:
- creation from portal and bot interaction;
- restricted Discord representation abstraction (private thread or restricted channel);
- participants;
- case ownership;
- teaching-team escalation;
- status;
- no public case-number lookup;
- analysis excluded by default;
- retention and closure hooks.

Use fixtures and service interfaces. If Discord permission semantics require live verification, write a technical-spike plan and tests around the local policy model instead of guessing.

## Acceptance criteria

Acceptance criteria:
- Public lookup adapter cannot return a Private Support case.
- Export/anonymization defaults exclude it.
- Permission assumptions are explicit.
- No production channel is created.

## Required completion report

Write `docs/reports/TASK-25-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
