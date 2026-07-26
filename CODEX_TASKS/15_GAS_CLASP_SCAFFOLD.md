# [Done] TASK-15: Create a local clasp-compatible Apps Script scaffold

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–14 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `apps/gas/`
- `docs/`
- `tests/`
- `docs/reports/`

You may also update `docs/reports/TASK-15-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Create a local Apps Script project scaffold managed by `clasp`.

Requirements:
- source under `apps/gas/src`;
- `appsscript.json`;
- local TypeScript or modern JavaScript build path;
- `doGet` and `doPost` routers;
- JSON/HTML response helpers;
- configuration wrapper using Script Properties at runtime;
- `.clasp.json.example`, never a real script ID;
- fixture mode;
- local tests for pure logic;
- deployment/runbook that names `ntusupercool@gmail.com` as intended owner/deployer.

Do not run interactive login, create a cloud project, deploy, or send requests to real Sheets/Discord.

## Acceptance criteria

Acceptance criteria:
- Local build/test succeeds without Google credentials.
- Cloud-only functions are isolated behind interfaces.
- No deployment ID or secret is committed.
- The code clearly states that GAS is not the Discord Gateway host.

## Required completion report

Write `docs/reports/TASK-15-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
