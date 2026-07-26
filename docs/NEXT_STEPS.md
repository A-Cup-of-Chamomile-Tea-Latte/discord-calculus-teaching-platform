# Ordered next steps

The local fixture prototype is complete. The next work is governance and bounded real-service evidence, not more feature breadth.

## P0 — before any real data, remote publication, or production credential

### 1. Appoint owners and close overdue decisions

- **Value:** establishes who may approve data use and respond to incidents.
- **Risk addressed:** remaining open decisions in U-005–U-015 and the high threat-model findings currently have role labels but no named accountable people.
- **Dependency:** none; this is the first action.
- **Deliverable:** update the decision register with `DECISION_NEEDED / ACCEPTED_RISK / CLOSED`, named owner, decision date, evidence link and review date.

Required decisions include public-case fields/rate limits, Portal access scope, Private Support mechanism, anonymous audit, GAS authority/transport, retention/deletion/backup, consent snapshots/withdrawal/release, and archive handling.

### 2. Review and establish the first Git baseline

- **Value:** creates traceability and enables remote CI review.
- **Risk addressed:** repository is unborn `main`, 0 commits/remotes, all files untracked.
- **Dependency:** archive decision U-015 and human content review.
- **Deliverable:** exclude or separately approve `project-exchange/*.zip`; review diagnostics and fixture-only claims; run fresh secret/real-data/archive scans; create a local baseline commit only with explicit user authorization; then separately decide whether to create/push a remote.

Do not treat the current 0-finding text scan as malware/binary-secret certification.

### 3. Implement and verify the accepted Portal access boundary

- **Value:** prevents public enumeration and makes the case experience usable with real data.
- **Risk addressed:** GitHub Pages is internet-public and cannot enforce course-session access; fixture builds currently include a case list and prebuilt case pages.
- **Dependency:** privacy/product owner and field/retention decisions.
- **Deliverable:** keep Pages as a public information shell with no real case data, remove production list/prebuilt case output, and use an authenticated backend for one-case lookup. If that boundary cannot be enforced, record a superseding hosting decision before implementation rather than silently weakening it.

### 4. Approve data lifecycle and consent governance

- **Value:** makes raw export, sanitized output, audit, contact and Private Support handling defensible.
- **Risk addressed:** no approved retention, deletion, backup, legal/incident hold or consent-withdrawal policy.
- **Dependency:** privacy/data owners.
- **Deliverable:** per-data-class retention; export-time and analysis-time consent snapshots; withdrawal/backfill rules; approved analysis destinations; human release approval; verified deletion and backup policy.

## P1 — first bounded real-service evidence

### 5. Run the read-only `dump_bot` test-guild spike

- **Value:** validates the narrowest real integration with the least write risk.
- **Risk addressed:** Discord permissions, Message Content availability, pagination, rate limits, audit and token revocation are unverified.
- **Dependency:** P0 owner/security approval and an isolated fictional test guild/application.
- **Scope:** one separate reader app, one allowlisted fictional thread, one explicit dump, no writer/Portal/Sheets/Private Support.
- **Rollback:** revoke the test token/app access and return the live adapter to fail closed.

### 6. Design the durable archive/export boundary

- **Value:** removes crash/retry ambiguity between read handoff, files and checkpoint.
- **Risk addressed:** in-memory sink/checkpoint/idempotency and multi-file crash window.
- **Dependency:** choose runtime/storage after the read-only spike.
- **Deliverable:** transactional SQLite journal, backend database/outbox or equivalent; operation markers; reconciliation; retention and encryption; tamper tests.

### 7. Exercise the writer and Private Support separately

- **Value:** validates thread creation, anonymous repost and restricted support without broad rollout.
- **Risk addressed:** role/channel overwrite, mention, notification, search and participant-revocation leakage.
- **Dependency:** reader evidence, incident owners and approved Private Support mechanism.
- **Deliverable:** separate writer app/token; fictional create/reply cleanup trace; Private Support visibility matrix and no-public-fallback test. Keep `BACKEND_ONLY` if any Discord mechanism fails.

## P2 — authenticated data services

### 8. Select and spike the authenticated Portal→backend/GAS transport

- Resolve execute-as-owner authority, origin/redirect/CORS, session/CSRF/replay, rate limits and kill switches.
- Keep Apps Script `access=MYSELF` until the design is reviewed; never use `no-cors`, JSONP or browser-held secrets.

### 9. Approve curated storage and batch endpoint

- Decide between dedicated `AnalysisMessages`/`AnalysisSummaries` sheets and a protected backend/object store.
- Keep manifests and curated content in separate access classes.
- Implement atomic row idempotency, locking, audit, partial-failure reconciliation, quota handling, backup/restore and delete tests.

### 10. Complete identity, email and activation production providers

- Use authenticated routes, enrollment authority, peppered verifier storage, CAS/outbox, generic anti-enumeration responses, multi-dimensional limits and provider quota circuit breakers.
- Email control alone must not grant course membership.

## P3 — release hardening

### 11. Reproduce CI from a clean baseline

- Run `npm ci` and a Python 3.12 clean environment; consider a hash-locked Python dependency file and SHA-pinned Actions.
- Make all six jobs required before merge only after the remote and access policy are approved.
- Resolve five local extraneous WASM packages by using a clean install, not by editing the lockfile blindly.

### 12. Conduct staging rehearsal and independent review

- Run the complete fictional submit→lookup→reply→export→sanitize→human review→import journey.
- Exercise token leak, Private Support leakage, export mis-send and provider outage rollback.
- Verify deletion and consent withdrawal.
- Obtain professor/institution/privacy review of student/TA guides and proposal wording.

## Safe work that can continue now

- Fixture/local demo, tests, docs and proposal linguistic polishing.
- Additional contract/tamper/abuse tests that require no external service.
- A fresh non-Git handoff scan and archive inventory.

Do not use real student data, create production credentials, publish case data, deploy, send email, connect a real course Discord server or send any export to an LLM without the P0 approvals.
