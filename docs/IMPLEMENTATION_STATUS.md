# Implementation status

Last repository verification: 2026-08-19 22:14 (Asia/Taipei)

Last Mac runtime process verification: 2026-08-19 22:14 (Asia/Taipei)

Canonical root: `/Users/chamomiletea/Documents/Curricular/115-1/Calculus TA/Discord_微積分模組教學優化專案`

Current branch: `codex/phase-2c-24h-production-integration`

## Current runtime

- `course_assistant` and `dump_bot` are active as single LaunchAgent instances on the Mac.
- Their logs use `~/Library/Logs/DiscordCalculus/`; the prior Documents log path was removed from the LaunchAgent configuration because macOS TCC caused exit 78.
- No live cutover has occurred. The Mac remains the only production writer until the operator sends the exact `GO-LIVE-CUTOVER` gate.
- The tracked runtime is `runtime/discord-course-bots/`; remote systemd deployment is ready in code but has not started because no SSH／Tailscale target has been supplied.

## Discord infrastructure

- The allowlisted Guild has the requested Admin, Staff／TA, Verified Member and Guest roles.
- Information, Question, Community, Private Support, Voice Chat and Staff categories and their managed channels are applied.
- Old bootstrap categories, channels, roles and test data were removed after live verification.
- `dump_bot` remains read-only or hidden on active managed channels.

## Data authority and SQLite

- Local SQLite is the sole operational authority. Google Sheets is a compact projection and temporary recovery／sharing surface.
- The tracked SQLite schema is at migration v5 with a checksum ledger, lifecycle events, reliable outbox／queue, service health and production projection stream.
- Case create／close／reopen and their projection-outbox rows are committed in the same transaction.
- Google failure degrades only the bridge; Discord can continue writing to SQLite and pending projection work remains durable.

## Google Sheets and GAS

- Sheet schema `2.0.0` is applied to `Server Database`.
- Migration receipt: 44 planned changes → 44 applied → second dry-run no-op.
- The workbook contains five visible human views (`Overview`, `CaseBoard`, `Members`, `Operations`, `History`) and five hidden machine views. The prior 21 empty managed tabs were removed.
- The standalone GAS is a real owner-only `executionApi` deployment under the shared standard GCP project. The historical `webapp` manifest was replaced.
- The standalone bundle exposes only the owner-operated bootstrap and Bridge functions. Retired `doGet`／`doPost` and transitional alias globals are absent, and the build rejects their return.
- Desktop OAuth uses only the Google Sheets scope. Client and refresh credential files live under ignored `.local/phase2c-oauth/` with mode `0600`.
- `bridgeConfigureTarget` validates the canonical 10-tab schema before writing Script Properties and removes the legacy `PHASE2B_*` target properties.
- Real `scripts.run` receipts are green: health, synthetic preview, synthetic apply, outbox completion and idempotent no-work replay.
- Bound GAS status-digest code and tests are complete, but its trigger remains disabled until a remote heartbeat is stable; enabling it now would create false stale alerts.

## Verification

- Full Python suite: 242 tests passed with two upstream Python 3.14 deprecation warnings; Ruff check, format and strict mypy passed.
- Portal／Config Studio／GAS: 53／3／58 tests passed; both Astro checks, GAS typecheck and all workspace builds passed.
- Secret scan: 626 candidate files, 0 findings.
- Mac bot single-instance check passed; both LaunchAgents remain active and have never exited.
- Compact Sheet migration and local real-cloud synthetic round-trip passed.
- `.local/` remains Git-ignored; no credential or live data was added to the repository.

## Remaining gates

- SSH／Tailscale host identity: blocked pending operator input.
- Remote staging and real-cloud smoke: blocked pending SSH.
- Remote SQLite backup／restore rehearsal: blocked pending remote staging.
- Live cutover: not started; requires exact `GO-LIVE-CUTOVER`.
- Post-cutover observation: not started; must run for a real 24 hours.

Detailed current report: `project-exchange/18_PHASE_2C_24H_HOST_PRODUCTION_INTEGRATION_REPORT_2026-08-19.md`.
