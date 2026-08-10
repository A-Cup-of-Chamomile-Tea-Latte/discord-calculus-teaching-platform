# Ordered next steps

## Discord infrastructure complete

The requested role, category, channel and permission structure is applied. Live verify is green,
the second apply produced zero mutations and both bots are online.

## Next validation package

- Exercise one synthetic case in each of the three Question forums.
- Exercise one Private Support open/close/export/delete flow.
- Confirm `dump_bot` remains read-only and cannot create posts, reply or manage threads.
- Optionally add Manage Messages and voice-member moderation to the `Admin` role before assigning
  it to a non-owner; the current Guild owner is not restricted by the empty role permission bits.
- Keep raw Discord content, student identity, Email, attachments and Private Support data out of
  chat, Git, public ZIPs and LLM inputs.

Do not deploy the Portal, connect Email/OAuth/AI services or analyze real student data without a
separate instruction.

## Data-layer order

1. Review the repository evidence audit in `project-exchange/15_GAS_SQLITE_DRIVE_REPOSITORY_EVIDENCE_AUDIT_2026-08-10.md`.
2. Decide the authoritative owner for identity data and the exact SQLite ↔ Sheets projection.
3. Move or re-implement the local-only live runtime in a tracked package before adding production
   migrations; do not apply speculative migrations to the existing live DB.
4. Add a versioned SQLite migration ledger and durable job/outbox model in a disposable DB first.
5. Connect `CommandQueue` and `EmailQueue` to adapters only after dry-run, claim/lease and
   idempotency tests pass. `PROVIDER_ACCEPTED` must not be reported as inbox delivery.
6. Apply any Google Sheet schema only after reading a dry-run diff for the intended Spreadsheet.
