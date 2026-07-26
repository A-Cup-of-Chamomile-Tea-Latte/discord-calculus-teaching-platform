# [Done] TASK-33: Run final diagnostic and create ChatGPT handoff

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–32 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `docs/reports/`
- `docs/NEXT_STEPS.md`
- `docs/IMPLEMENTATION_STATUS.md`

You may also update `docs/reports/TASK-33-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Review the entire repository after all completed tasks.

Perform:
- full test/lint/build run;
- repository tree and size inventory;
- secret/real-data scan;
- stale TODO/FIXME inventory;
- dependency and mocked-service inventory;
- product decision drift check against shared context;
- documentation completeness check;
- GitHub Pages base-path build check;
- Apps Script cloud-readiness checklist;
- Discord live-spike readiness checklist;
- local exporter readiness check.

Create:
- `docs/IMPLEMENTATION_STATUS.md` with implemented/mocked/not-started;
- `docs/NEXT_STEPS.md` ordered by value, risk, and dependency;
- a concise handoff that the user can paste into ChatGPT for discussion.

Do not silently fix major architectural drift. Describe it and recommend a decision.

## Acceptance criteria

Acceptance criteria:
- All claims are backed by actual commands or file inspection.
- Test results are exact.
- External deployments are accurately marked not performed.
- The copy-paste handoff contains no secrets and asks only the highest-value questions.

## Required completion report

Write `docs/reports/TASK-33-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
