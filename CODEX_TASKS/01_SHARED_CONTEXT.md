# Shared product context and fixed decisions

This file is the current source of truth for all Codex tasks. Do not silently replace these decisions. When implementation reveals a problem, record it in a task report and in `docs/decisions/UNRESOLVED.md`.

## Product purpose

Build a lightweight teaching-support layer for NTU's modular calculus teaching. It should integrate discussion resources, lower the psychological and operational cost of asking questions, reduce duplicated one-to-one email work, support question tracking, and create structured records that can later be reviewed for teaching-quality analysis.

## Platform boundaries

- **NTU COOL** remains authoritative for course materials, homework, grades, deadlines, official announcements, and course policies.
- **Discord** is for questions, discussion, resource integration, TA responses, optional voice office hours, and community interaction.
- **The entrance portal** handles onboarding, privacy guidance, optional website-mediated question submission, public case lookup, private-support entry, user settings, and system status.
- **Google Sheets / Apps Script** are prototype and administration tools. They are not a robust high-frequency server database.
- **Local Python tools** perform explicit/manual exports, anonymization, report preparation, and batch upload.
- **No voice recording or automatic voice transcription** in the first version.

## Website-mediated questions

Students may post directly in Discord. Website submission is an alternative for students who do not want to open Discord to submit a question.

A website-submitted general question receives a human-readable case number and is mapped to a Discord forum post/thread. A student may search a general case from the portal homepage by case number and see its progress. Private Support cases are not exposed through the public case-number search.

Do not implement continuous polling of every case. The first version may use:
- fixture/mock data;
- explicit refresh;
- on-demand fetch for one case;
- manual/local export initiated by a manager.

## Identity and onboarding

- Discord OAuth2 binds a portal record to a Discord account and may authorize joining the server. It does not by itself prove NTU course membership.
- Email verification proves control of the submitted email address.
- NTU Mail may be used for institutional verification; Gmail may be stored as an optional reachable contact address.
- Manually approved exceptional members may receive a single-use **activation code**. Internally it is a nonce: single-use, expiring, auditable, and invalid after redemption.
- The course server nickname format is `nnmmm`: two-digit class code + three-digit joining order.
- A server nickname does not hide the Discord account's global username, display name, avatar, or profile. The user guide should recommend privacy settings, including disabling unsolicited DMs from shared-server members.
- Do not use roles as a general-purpose personal-data database. Roles are for permissions and broad membership groups.

## Author display and visibility

Keep these as separate concepts.

Author display modes:
- real name;
- course alias (`nnmmm`);
- anonymous to ordinary members but identifiable to authorized administrators.

Visibility modes:
- class;
- whole course;
- teaching staff only.

A fully anonymous author must not type a normal Discord reply that exposes their nickname. Use a website form or Discord modal, then let the bot repost. Never rely on “post first, delete immediately.”

## Cases and status

The exact case-number prefix remains configurable. Fixtures may use `CALC-000421`.

Initial status vocabulary:
- `OPEN`
- `WAITING_FOR_STUDENT`
- `ANSWERED`
- `ESCALATED`
- `CLOSED`

Do not invent many additional workflow states without an ADR.

## Private Support

Private Support is a separate case type and access path. It should use a private Discord mechanism or a restricted backend representation. It is excluded from teaching-analysis exports by default.

## Data export and later AI analysis

The immediate requirement is not real-time LLM processing. A manager should be able to explicitly dump or follow a selected Discord thread and export structured history with timestamps, authors/roles, reply relationships, edits, attachments, and consent metadata.

The current manual pain point is copying entire Discord conversations and pasting them into GPT. Replace that with repeatable JSON/Markdown exports.

General public course discussions may default to permitting pseudonymized teaching-quality analysis, with a visible account-level and per-post override. Private Support defaults to excluded. Do not implement model training or automatic scoring of students.

## Google tools

- Apps Script owner/deployer: `ntusupercool@gmail.com`.
- Sheets may hold users, memberships, consents, case indexes, activation codes, exports, audit records, and summaries.
- Do not synchronously write every Discord message to Sheets.
- Original messages should be exported deliberately to files, then optionally batch-imported using local Python or an Apps Script endpoint.
- `clasp` manages Apps Script source and deployments; it is not the data-upload mechanism.
- Never commit Google credentials, Discord tokens, OAuth secrets, deployment IDs, or real student data.

## Multi-bot direction

The architecture may support multiple Discord applications/bots:
- `course_assistant`: interactions and write operations;
- `archive_reader`: read-oriented case fetch and export;
- `moderation`: future placeholder;
- shared Python library for configuration, contracts, logging, and Discord helpers.

Each actual bot has its own token and least-privilege permission set. Do not run multiple competing processes with one token unless the architecture explicitly supports sharding and event ownership.

## Portal direction

Use Astro + TypeScript with static output suitable for a GitHub Pages project site. Use plain CSS/design tokens initially. Do not start from a large visual template. First build accessible information architecture, reusable components, and a clean low-fidelity interface; visual themes can be applied later.

The existing account/organization site repository is already occupied. A new repository should be treated as a GitHub Pages **project site**, not as a replacement for the existing owner site.

## Safety and scope

- Use fixtures only.
- No production Discord writes.
- No public deployment, remote repository creation, OAuth registration, Apps Script cloud creation, or email sending without explicit confirmation.
- Prefer reversible local work.
- Record assumptions and diagnostics instead of blocking on minor uncertainty.
- Every task must produce a report that can be pasted back into ChatGPT.
