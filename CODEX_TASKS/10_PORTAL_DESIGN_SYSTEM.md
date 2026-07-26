# [Done] TASK-10: Create low-fidelity portal design system

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–09 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `apps/portal/src/styles/`
- `apps/portal/src/components/`
- `apps/portal/docs/`
- `docs/reports/`

You may also update `docs/reports/TASK-10-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Create a clean low-fidelity visual foundation without importing a large theme.

Define:
- CSS design tokens for spacing, typography, radii, borders, focus, and semantic states;
- responsive layout primitives;
- accessible form controls;
- buttons;
- cards;
- case status badges;
- visibility/author-mode labels;
- alert and fallback components;
- navigation and footer;
- loading, empty, error, and success states.

Use plain CSS or scoped Astro CSS. Do not add Tailwind or a component library unless the report proves a concrete need. Avoid final branding decisions and custom illustrations.

Create a static component gallery or Storybook-like page using fixtures, but do not add heavy tooling just for the gallery.

## Acceptance criteria

Acceptance criteria:
- Components are keyboard accessible and have visible focus.
- Mobile layout is treated as primary.
- No color alone communicates status.
- Styling can later be re-themed using tokens.
- The result is presentable but intentionally low fidelity.

## Required completion report

Write `docs/reports/TASK-10-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
