# [Done] Batch E EXPORT — autonomous Codex run

Run the local export/anonymization/import lane after Tasks 07–08 and preferably Task 21. Use fixtures and no external credentials.

## Instructions

1. Read `CODEX_TASKS/00_START_HERE.md` and `CODEX_TASKS/01_SHARED_CONTEXT.md`.
2. Process these task files in order:

- `CODEX_TASKS/26_LOCAL_EXPORT_PIPELINE.md`
- `CODEX_TASKS/27_ANONYMIZATION_CONSENT.md`
- `CODEX_TASKS/28_SHEETS_BATCH_IMPORTER.md`

3. Finish each task completely before starting the next.
4. Run the task-specific tests/builds.
5. Write the required report after each task:

- `docs/reports/TASK-26-REPORT.md`
- `docs/reports/TASK-27-REPORT.md`
- `docs/reports/TASK-28-REPORT.md`

6. Do not push, deploy, create cloud resources, send email, use real data, or request secrets.
7. When a task is blocked by a missing external resource, create the local interface/mock/documentation, report the blocker, and continue to the next task only when doing so is safe.
8. Prefer local commits after each completed task only if Git identity is already configured and the worktree is clean. Never push.
9. At the end, write `docs/reports/BATCH-E_EXPORT-SUMMARY.md` with:
   - completed tasks;
   - skipped/blocked tasks;
   - exact test/build results;
   - key diagnostics;
   - product/architecture questions;
   - next recommended batch;
   - a concise Traditional Chinese copy-paste summary for ChatGPT.
