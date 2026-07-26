# [Done] TASK-18: Implement single-use activation-code logic

## Codex operating instruction

Work locally in:

`/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord 微積分模組教學優化專案`

Before editing, read:
- `PROJECT_DEFAULTS.md`
- `CODEX_TASKS/01_SHARED_CONTEXT.md`
- Tasks 01–17 reports where applicable
- this task

Do not perform external or destructive actions. Use fixtures and local files only. Do not ask minor clarification questions: choose the most reversible interpretation, record it as an assumption, and continue. Stop before any action that would publish, deploy, send email, create a remote resource, connect to a real Discord server, or require a real secret.

## Primary allowed paths

- `apps/gas/`
- `contracts/`
- `fixtures/`
- `tests/`
- `docs/reports/`

You may also update `docs/reports/TASK-18-REPORT.md`. Avoid unrelated edits. If a required prerequisite is missing, implement only a safe stub and report the dependency.

## Objective and work

Implement the domain logic for manually issued activation codes.

Properties:
- human-enterable code format;
- cryptographically strong random source when available;
- store only a hash/fingerprint, not plaintext after issuance;
- optional binding to email or Discord user ID;
- role/permission profile;
- creation, expiration, redemption, revocation;
- atomic single-use behavior;
- audit event;
- safe fixture/deterministic test mode.

Student-facing term is `啟動碼`; internal documentation may call it a nonce. Do not call it a password.

Because Sheets lacks robust transactions, document race conditions and implement the strongest reasonable lock/idempotency method for the prototype. Do not claim production-grade concurrency.

## Acceptance criteria

Acceptance criteria:
- Tests prove a code cannot be redeemed twice.
- Expired/revoked/wrong-bound codes fail.
- Plaintext is shown only at creation in test/demo output.
- Concurrency limitation is documented honestly.

## Required completion report

Write `docs/reports/TASK-18-REPORT.md` using `CODEX_TASKS/TEMPLATE_TASK_REPORT.md`.

The final report must include a Traditional Chinese copy-paste handoff for discussion with ChatGPT. State exactly what was implemented, what remains mocked, test/build results, diagnostics, and the recommended next task.
