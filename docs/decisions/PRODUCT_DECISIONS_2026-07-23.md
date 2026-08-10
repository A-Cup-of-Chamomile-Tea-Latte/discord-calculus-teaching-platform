# Product decisions accepted through 2026-08-10

Source: `project-exchange/Discord_Project_Next_Discussion_and_Codex_Package/01_PRODUCT_DECISIONS_UPDATE.md`.

This record promotes only the decisions explicitly fixed by the handoff. Open questions remain in `docs/decisions/UNRESOLVED.md`.

## Responsibility boundaries

- NTU COOL remains the system of record for course materials, assignments, grades, deadlines, official announcements, and policy.
- Discord is a supplementary discussion/collaboration surface.
- The Portal is an optional low-friction intermediary; students may still use Discord directly.
- GitHub Pages is only a static entry surface. Production must not prebuild real case data into public pages.

## Case representation

- Public form: `C12-7K4M2Q-0907-2007`.
- Non-standard class: `C99-R8N6WX-0907-2007`.
- Private Support suffix: `C12-7K4M2Q-0907-2007-P`.
- The token is random and is never derived from a name, student number, email address, or Discord identifier.
- Production lookup is one case at a time. A successful result may mask the token while preserving enough disambiguation.
- An internal UUID and Discord/database identifiers remain separate from the display number.

## Reduced projection

The first Portal review screen is desktop-first and intentionally smaller than Discord. It may show case/status, update/response/read/sync times, the latest teaching response, timeline, text conversation, attachment markers, Discord deep link, close, and follow-up controls.

`Last Update` includes any case change. `Last Response` includes only a teaching-team text response. Attachment bodies are not downloaded, proxied, or rehosted in this phase.

## Synchronization and lifecycle

- Gateway changes enqueue changed cases; changed projections are written in small batches.
- Active-case reconciliation is periodic and bounded; weekly work handles archive/export/analysis maintenance.
- A web lookup reads the projection and does not replay complete Discord history.
- Supported lifecycle states are `OPEN`, `ANSWERED`, `TEMPORARILY_CLOSED`, `CLOSED`, and `REOPENED`.
- Manual and automatic closure sources are distinct. Verified-read-based rules remain behind an interface until the verification method is approved.
- Discord thread auto-archive is not the product closure state.

## AI-analysis choice

- Every case requires an explicit Yes or No; there is no preselected checkbox.
- The original poster's No excludes the entire case from the AI-analysis pipeline.
- The original poster's Yes establishes only case-level eligibility; per-author message filtering remains available.
- Database state is authoritative. Discord tags/icons are projections only.

## Bot and data boundaries

- `course_assistant` owns writer/onboarding/case-status behavior.
- `dump_bot` is the read-oriented successor name for `archive_reader` and supports selected fetch, explicit dump/follow, bounded reconciliation, weekly export, and structure inventory without continuous polling.
- Working data and long-term archive data are separated. Sheets/GAS remain a fixture/mock spike until access, quota, storage, and governance gates are approved.

## Non-negotiable constraints

No recording, automatic voice transcription, all-server continuous polling, automatic all-content LLM submission, real-case static publication, committed secrets, or unreviewed merging of Private Support with normal cases.

## 2026-08-10 data authority and cloud operations

- The local database is the primary operational authority. Google Sheets may accept managed writes,
  but serves sharing, administrative projection and temporary restore rather than automatic
  replacement of local state.
- Any Sheet-to-local fetch or restore must validate the schema version, source revision, integrity
  evidence, timestamps and expected dataset identity, then require an explicit human confirmation.
  A conflict starts from the verified local version; cloud state never silently wins.
- Drive archive structure may begin with a migration-friendly layout and be revised when operating
  evidence reveals a better lifecycle. Folder naming is not an authority boundary.
- Email status `SENT` means the approved sender call returned successfully and the local audit write
  completed. It describes completion of this system's send responsibility, not inbox delivery or
  recipient reading.
- Student numbers, names and other identifying material are protected data. AI analysis requires
  explicit student consent, appropriate de-identification and a teaching-improvement-only purpose.
  Detailed retention, withdrawal and redaction procedures remain to be specified before real-data
  analysis.
