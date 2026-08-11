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
2. **Decided and implemented locally:** SQLite is the operational authority. Sheets schema 2.0.0
   is a compact cloud projection with five human and five hidden machine views. Cloud → local
   still requires version/checksum/source validation and explicit confirmation.
3. **Completed locally:** the live-tested source has a canonical tracked package at
   `runtime/discord-course-bots/`; live LaunchAgents still use the old copy until a separate
   backup/dry-run/cutover gate.
4. **Completed in disposable databases:** checksum-verified migrations and a reliable Private
   Support dump job queue. The existing live DB remains untouched.
5. **USER ACTION REQUIRED — the single next step:** in Chrome profile `Ding Ding`, run the bound
   menu compact-migration dry-run, apply only if it reports no blocker, then rerun dry-run and
   capture the compact dry-run/apply/no-op receipt. Do not enter the Phase 2B sidebar yet.
6. **Completed in synthetic code/fake transport:** the local → Sheets projection adapter,
   authenticity receipt, one-shot CLI, fixed-action `_CommandInbox` flow and GAS preview/apply/
   claim/ack functions. A real cloud smoke test remains blocked until step 5 is evidenced.
7. `_EmailOutbox` remains outside Phase 2B. Do not connect it or automatic cloud → local writes.
   `providerAcceptedAt` / product state `SENT` must not be reported as inbox delivery.
8. **Interactive foundation completed:** use Portal `/sqlite-lab/` before the first hands-on
   database session. Then run `discord-db-inspect` and four read-only queries against a disposable
   database; do not use live row dumps as teaching material.

Phase 2B operator guide: `docs/PHASE2B_DATA_LAB_GUIDE.md`.
