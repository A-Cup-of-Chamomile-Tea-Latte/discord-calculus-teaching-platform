# [Done] TASK-29: Perform security, privacy, and abuse review

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–28 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `docs/security/`
- `docs/decisions/`
- `docs/reports/`

You may also update `docs/reports/TASK-29-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Review the current local implementation and write a practical threat model.

Cover:
- server nickname vs Discord profile visibility;
- unsolicited DMs and user-guide recommendation;
- public case-number search;
- anonymous author traceability;
- activation-code sharing/replay;
- email verification and contact data;
- bot token separation and least privilege;
- GAS deployed-as-owner implications;
- Sheets access;
- cross-origin portal/GAS calls;
- Private Support permissions;
- exports and local files;
- consent and AI handoff;
- fixtures/secrets in Git;
- abuse/spam and rate limits;
- incident/fallback instructions.

Classify findings by severity and mark each as fixed, mitigated, accepted for prototype, or unresolved. Do not claim legal compliance or production readiness.

## Acceptance criteria

Acceptance criteria:
- Findings reference concrete files/components.
- High-severity issues have an owner and next action.
- The review distinguishes prototype risk from production blockers.
- A user-facing privacy/DM guide draft is included.

## Required completion report

Write `docs/reports/TASK-29-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
