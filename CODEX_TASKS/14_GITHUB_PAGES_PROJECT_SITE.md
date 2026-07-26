# [Done] TASK-14: Prepare GitHub Pages project-site deployment

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–13 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `apps/portal/`
- `.github/workflows/`
- `docs/`
- `docs/reports/`

You may also update `docs/reports/TASK-14-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Prepare—but do not execute—a GitHub Pages project-site deployment.

Assumptions to verify:
- owner currently appears to be `A-Cup-of-Chamomile-Tea-Latte`;
- suggested repository name is `discord-calculus-teaching-platform`;
- the existing owner site repository must not be replaced.

Implement:
- Astro `site` and `base` configuration via safe environment/build variables;
- a GitHub Actions Pages workflow;
- build artifact upload;
- path-safe links/assets for `/<repository>/`;
- deployment documentation;
- a custom-domain migration note for later;
- a dry-run/build verification.

Do not create the remote repository, enable Pages, push, or deploy. Report the expected project-site path pattern and every manual action that remains.

## Acceptance criteria

Acceptance criteria:
- Local production build works with a non-root base path.
- All internal links and assets survive the base path.
- The workflow contains least permissions and no secrets.
- Existing owner-site files are untouched.

## Required completion report

Write `docs/reports/TASK-14-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
