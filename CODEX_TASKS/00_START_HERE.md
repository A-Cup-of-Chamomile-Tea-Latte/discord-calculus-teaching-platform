# Start here — Codex execution guide

## Intended location

Work inside:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

The path is acceptable. Quote it because it contains spaces and Traditional Chinese characters.

## First rule

Before every task, read:

1. `PROJECT_DEFAULTS.md`
2. `CODEX_TASKS/01_SHARED_CONTEXT.md`
3. reports from prerequisite tasks
4. the selected task file

Do not silently make unresolved product decisions. Use conservative, reversible defaults and document assumptions.

## Required report after every task

Write `docs/reports/TASK-XX-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`. The report must include:

- summary;
- files changed;
- commands run;
- tests and exact results;
- diagnostic findings;
- assumptions;
- risks or blockers;
- unresolved questions;
- concrete next-step recommendations;
- a concise copy-paste block for discussion with ChatGPT.

## External-action policy

Do not:
- push to GitHub;
- create or publish a GitHub repository;
- deploy GitHub Pages;
- create or deploy a cloud Apps Script project;
- send email;
- connect to a production Discord server;
- use real student information;
- request or expose secrets.

Local commits are optional. Make them only when Git is initialized, the worktree is clean, and user identity is already configured. Never push.

## Execution order

### Foundation — sequential
- 02 Initial diagnostic
- 03 Monorepo scaffold
- 04 Toolchain and quality baseline
- 05 Project charter and glossary
- 06 Architecture decision records
- 07 Data contracts
- 08 Fixtures and mock adapters

### Parallel lanes after Task 08
- Portal: 09–14
- Apps Script / Sheets: 15–19
- Discord bots: 20–25
- Local export: 26–28

### Review and integration
- 29 Security/privacy
- 30 Testing/CI
- 31 Documentation/demo/preface
- 32 Integration plan
- 33 Final diagnostic

Use the batch files to run a coherent group of tasks. Do not run parallel lanes in the same worktree at the same time unless separate Git worktrees/branches are used.
