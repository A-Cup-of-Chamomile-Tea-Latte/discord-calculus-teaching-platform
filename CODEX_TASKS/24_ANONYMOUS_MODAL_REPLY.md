# [Done] TASK-24: Prototype anonymous modal-based reply

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–23 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `bots/course_assistant/`
- `bots/common/`
- `tests/`
- `docs/reports/`

You may also update `docs/reports/TASK-24-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Prototype the safe anonymous reply interaction.

Flow:
- authorized user presses a button or runs an interaction;
- bot opens a Discord modal;
- user submits text privately through the interaction;
- service verifies case ownership/permission;
- bot reposts using the case's display mode;
- response to the submitter is ephemeral;
- audit metadata records the authorized actor without exposing them publicly.

Do not implement “send a normal message and delete it.” Add length limits, empty-content validation, anti-duplicate idempotency, and a fixture demonstration. Clearly separate course-alias mode from fully anonymous mode.

## Acceptance criteria

Acceptance criteria:
- Fixture test shows the original user message never appears as a normal public message.
- Unauthorized users cannot append to another person's anonymous case.
- Public output contains no Discord username/user ID.
- Admin traceability remains represented in the private record.

## Required completion report

Write `docs/reports/TASK-24-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
