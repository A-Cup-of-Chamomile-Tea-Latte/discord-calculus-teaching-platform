# [Done] TASK-13: Prototype onboarding, question submission, and support forms

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–12 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `apps/portal/`
- `fixtures/`
- `tests/`
- `docs/reports/`

You may also update `docs/reports/TASK-13-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Build non-production form prototypes using fixture/mock submission.

Join/setup fields:
- Discord connection placeholder;
- NTU email;
- optional contact Gmail;
- class selection;
- assigned `nnmmm` preview;
- rules/privacy acknowledgement;
- analysis default;
- DM privacy recommendation.

Ask-through-portal fields:
- title;
- question content;
- class/course/teaching-staff visibility;
- real name/alias/anonymous display;
- analysis permission;
- attachment metadata placeholder;
- confirmation that NTU COOL remains authoritative.

Private Support:
- separate route and warning;
- no public case lookup;
- analysis excluded by default.

Validation should be clear and non-punitive. Do not actually send email, contact Discord, or upload files.

## Acceptance criteria

Acceptance criteria:
- All forms work in fixture mode and provide confirmation screens.
- The user can distinguish general question vs Private Support.
- Fully anonymous follow-up is described as website/modal-mediated.
- No personal data is persisted in browser storage by default.

## Required completion report

Write `docs/reports/TASK-13-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
