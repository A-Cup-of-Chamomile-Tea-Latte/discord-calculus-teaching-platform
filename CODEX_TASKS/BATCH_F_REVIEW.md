# [Done] Batch F REVIEW — autonomous Codex run

Run the audit/integration/final-handoff lane after the other completed lanes. Do not conceal failed checks or incomplete integrations.

## Instructions

1. Read `CODEX_TASKS/00_START_HERE.md` and `CODEX_TASKS/01_SHARED_CONTEXT.md`.
2. Process these task files in order:

- `CODEX_TASKS/29_SECURITY_PRIVACY_THREAT_MODEL.md`
- `CODEX_TASKS/30_TESTING_CI.md`
- `CODEX_TASKS/31_DOCUMENTATION_DEMO_PREFACE.md`
- `CODEX_TASKS/32_INTEGRATION_PLAN.md`
- `CODEX_TASKS/33_FINAL_DIAGNOSTIC_HANDOFF.md`

3. Finish each task completely before starting the next.
4. Run the task-specific tests/builds.
5. Write the required report after each task:

- `docs/reports/TASK-29-REPORT.md`
- `docs/reports/TASK-30-REPORT.md`
- `docs/reports/TASK-31-REPORT.md`
- `docs/reports/TASK-32-REPORT.md`
- `docs/reports/TASK-33-REPORT.md`

6. Do not push, deploy, create cloud resources, send email, use real data, or request secrets.
7. When a task is blocked by a missing external resource, create the local interface/mock/documentation, report the blocker, and continue to the next task only when doing so is safe.
8. Prefer local commits after each completed task only if Git identity is already configured and the worktree is clean. Never push.
9. At the end, write `docs/reports/BATCH-F_REVIEW-SUMMARY.md` with:
   - completed tasks;
   - skipped/blocked tasks;
   - exact test/build results;
   - key diagnostics;
   - product/architecture questions;
   - next recommended batch;
   - a concise Traditional Chinese copy-paste summary for ChatGPT.
