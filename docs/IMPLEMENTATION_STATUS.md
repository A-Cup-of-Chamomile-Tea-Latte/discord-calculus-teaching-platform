# Implementation status

Last repository/data-layer verification: 2026-08-10 23:20 (Asia/Taipei)

Last Discord live verification: 2026-07-30 20:18 (Asia/Taipei)

Canonical root: `/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案`

## Current status

At the last Discord live verification, the allowlisted test Guild was connected and the two
runtime bots were online:

- `DC-Calculus-Manager` (`course_assistant`)
- `DC-Calculus-Archive` (`dump_bot`)

The former fixture-only Discord provisioning planner has been replaced by one allowlisted,
rerunnable live CLI. The requested infrastructure is fully applied, live verify is green and a
second apply produced zero mutations.

## Applied Discord infrastructure

- Roles created: `Admin`, `Staff / TA`, `Verified Member`, `Guest`.
- Categories created: Information, Question, Community, Private Support, Voice Chat and Staff.
- All 15 requested child channels created, including the three managed Question forums.
- `welcome` fixed message and `伺服器使用總則 / Server Guidelines` forum post created.
- BOT LAB, old test PRIVATE SUPPORT, old bootstrap roles/data and the approved old default
  Information/Text/Voice categories were removed.
- `dump_bot` is effectively read-only or hidden on all currently active managed channels.
- `/lab bootstrap` is no longer registered by the runtime bot.

The final role order is:

`Admin > Staff / TA > DC-Calculus-Manager > Verified Member > Guest > DC-Calculus-Archive`.

`Staff / TA` has Manage Messages and voice-member moderation. Advisory: the `Admin` role itself
does not carry those bits; this does not restrict the current Guild owner, but they should be
added before assigning Admin to a non-owner.

## Commands

```bash
.venv/bin/python -m tools.discord_provisioning inventory --guild-id <TEST_GUILD_ID>
.venv/bin/python -m tools.discord_provisioning apply --guild-id <TEST_GUILD_ID> --reset-lab
.venv/bin/python -m tools.discord_provisioning verify --guild-id <TEST_GUILD_ID>
```

The live runtime currently uses the Python environment under
`.local/discord-course-bots-runtime/.venv`; the repository `.venv` also contains the required
dependencies.

## Verification

- Live resource replay: zero mutations on the second completed apply.
- Live verify: passed with zero errors and zero warnings.
- Root Python suite: 164 tests expected after removal of obsolete provisioning tests.
- Runtime bot suite: 25 passed; 28 known Python 3.14 / pytest-asyncio deprecation warnings.
- Ruff and secret scan: passed.

Detailed result:
`docs/reports/DISCORD_INFRASTRUCTURE_PROVISIONING_REPORT_2026-07-30.md`

## Data-layer evidence audit

- The live runtime source is local-only under `.local/discord-course-bots-runtime/`; it is not
  fully identified by the current Git HEAD.
- Its executable SQLite initializer currently creates five tables: `runtime_config`, `drafts`,
  `cases`, `private_support` and `private_dump_jobs`.
- The live schema has no foreign keys, schema migration table, deadline, claim/lease, retry,
  outbox or Google sync columns. `PRAGMA user_version` is `0`.
- A canonical tracked runtime now exists at `runtime/discord-course-bots/`, but the live
  LaunchAgents have not been cut over to it. Its disposable-database implementation has a
  checksum-verified migration ledger through version 3 and a Private Support dump queue with
  atomic claim, lease/heartbeat, safe error codes, retry/backoff and stale-token protection.
- The version-3 implementation is covered by isolated tests only; it has not migrated or opened
  the live SQLite file.
- The tracked monorepo contains a broader fixture-first contract and GAS prototype. It must not
  be described as the live bot database.
- GAS Sheets schema `2.0.0` replaces the overbuilt 21-tab prototype with five human views
  (`Overview`, `CaseBoard`, `Members`, `Operations`, `History`) and five hidden machine views.
  It stores sufficient statistics and opaque references only; raw messages, names, student IDs,
  email addresses, attachments, logs and credentials remain outside Sheets.
- The compact migration performs a full preflight. Any data row in an old managed tab, or any
  operator-owned legacy `Settings` key, blocks all mutations. Only exact empty legacy tabs may be
  deleted; unknown tabs are preserved. Local tests cover apply, blocker, preservation and no-op.
- Both GAS projects are at immutable version 3 with exact push/pull-back fingerprints. The
  standalone owner-only fixture deployment is on v3. The bound Sheet operator apply is awaiting
  the explicit in-Sheet menu confirmation; no Email or real-data sync has been enabled.
- Canonical runtime now provides `discord-db-inspect`, which opens SQLite read-only and reports
  schema version, tables, columns and row counts without querying or printing row values.
- Portal now includes a local-only `/sqlite-lab/` interactive learning environment: carrier map,
  schema explorer, allowlisted synthetic SQL simulator, transaction failure comparison, reliable
  queue takeover sequence, carrier/authenticity exercises, final knowledge check and device-local
  progress. It does not open a database or send/store learner responses externally.
- The evidence audit and implementation handoff is recorded in
  `project-exchange/15_GAS_SQLITE_DRIVE_REPOSITORY_EVIDENCE_AUDIT_2026-08-10.md`.
