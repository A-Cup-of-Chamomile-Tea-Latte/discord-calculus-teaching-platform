# [Done] TASK-09: Design portal information architecture and user journeys

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–08 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `apps/portal/docs/`
- `docs/architecture/`
- `docs/reports/`

You may also update `docs/reports/TASK-09-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Design before styling or framework implementation.

Document:
- route map;
- navigation hierarchy;
- student journeys for direct Discord posting, website-mediated posting, public case lookup, private support, onboarding, and privacy guidance;
- teaching-team journey for case triage;
- failure and fallback journeys;
- what each page owns and explicitly does not own;
- where links return users to NTU COOL or Discord;
- which pages are static and which require a backend adapter.

Required initial routes/sections:
- home;
- case search;
- case detail;
- join/setup;
- ask through portal;
- private support;
- user guide/privacy;
- system status.

Specify public/private boundaries. Include wireframe-level text outlines and a content inventory. Do not select a visual template.

## Acceptance criteria

Acceptance criteria:
- A professor can understand the flow from the diagrams.
- The home page has a prominent case-number search.
- Website submission is labeled as an alternative.
- Private Support cannot be reached through public case search.
- NTU COOL authority is visible where relevant.

## Required completion report

Write `docs/reports/TASK-09-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
