# Ordered next steps

## Current stopping point

Local implementation, compact Sheet migration, Desktop OAuth and the local real-cloud synthetic round-trip are complete. Do not repeat the 44-action Sheet migration or create another OAuth client.

The existing Mac `course_assistant` and `dump_bot` remain the only live writers. Corpus／LLM analysis is not part of Phase 2C.

## Next external input

Provide all three host identity fields:

1. SSH username.
2. Tailscale hostname or private IP.
3. Expected SSH host-key fingerprint. If it has not been recorded, the operator must verify it during the first connection.

Do not send a password, private SSH key, Discord token or OAuth credential through chat.

## Work after host identity is available

1. Run the read-only host audit: OS, time sync, disk, memory, Python, systemd, Tailscale, existing services and host key.
2. Install the Phase 2C release into remote staging without stopping the Mac bots.
3. Transfer only the required protected environment and OAuth credential through the approved secret path; keep permissions owner／service-readable.
4. Run remote synthetic SQLite → GAS preview／apply／no-work smoke tests.
5. Perform a consistent SQLite backup and restore rehearsal to a different path, then verify `integrity_check`, migration ledger and row counts.
6. Present a readiness summary. Stop here until the operator sends the exact `GO-LIVE-CUTOVER` string.

## Work after `GO-LIVE-CUTOVER`

1. Stop and verify zero Mac writers.
2. Create the final consistent live SQLite backup and checksum.
3. Transfer and restore the database on the remote host; verify integrity before starting services.
4. Start one remote `course_assistant`, one `dump_bot` and one `data_bridge` systemd unit.
5. Verify Discord connectivity, one-writer invariants, queue depth, GAS heartbeat and compact Sheet projection.
6. Enable the bound GAS status-digest trigger only after the remote heartbeat is stable.
7. Observe the system for a real 24 hours and update the existing Phase 2C report in place.

## Safety boundaries

- Local SQLite remains authority; Sheets is not allowed to overwrite it without version, checksum, source and operator-confirmation checks.
- Keep raw Discord messages, names, student IDs, email addresses, attachments, Private Support content and credentials out of chat, Git, public ZIPs and LLM inputs.
- Production command inbox remains fail-closed; arbitrary cloud-to-local commands are out of scope.
- No public SSH, public GAS endpoint, second production writer or live cutover before its explicit gate.
