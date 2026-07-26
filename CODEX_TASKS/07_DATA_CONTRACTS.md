# [Done] TASK-07: Define shared JSON contracts and enums

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–06 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `contracts/`
- `tests/contract/`
- `docs/architecture/`
- `docs/reports/`

You may also update `docs/reports/TASK-07-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Define versioned, language-neutral JSON Schemas for the project's shared records.

At minimum:
- User
- VerifiedEmail
- DiscordAccount
- CourseMembership
- Case
- CaseMessage
- Consent
- ActivationCode
- ExportManifest
- AuditEvent
- CaseLookupResponse

Required concepts:
- configurable case number;
- public vs private-support case type;
- class/course/teaching-staff visibility;
- real-name/course-alias/anonymous display mode;
- status enum from shared context;
- account default and per-post analysis permission;
- Discord thread/message mapping;
- timestamps with timezone;
- source (`PORTAL`, `DISCORD`, `BOT`, `IMPORT`);
- schema version;
- no raw secret values.

Create example valid and invalid instances and contract validation tests. Document compatibility rules and how to evolve schemas.

## Acceptance criteria

Acceptance criteria:
- Schemas validate all fixture examples.
- Invalid examples fail for a stated reason.
- Private Support defaults to analysis excluded.
- IDs are clearly distinguished from display labels.
- Contracts do not expose OAuth access tokens or activation-code plaintext.

## Required completion report

Write `docs/reports/TASK-07-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
