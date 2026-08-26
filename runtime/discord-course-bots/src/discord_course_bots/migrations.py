from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass

from discord_course_bots.repository_time import utc_now_iso


class MigrationError(RuntimeError):
    """The database schema cannot be safely brought to the expected version."""


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    fingerprint: str
    apply: Callable[[sqlite3.Connection], None]

    @property
    def checksum(self) -> str:
        source = f"{self.version}\n{self.name}\n{self.fingerprint}"
        return hashlib.sha256(source.encode()).hexdigest()


BASELINE_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS runtime_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS drafts (
        thread_id INTEGER PRIMARY KEY,
        forum_channel_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        original_title TEXT NOT NULL,
        starter_message_id INTEGER,
        setup_message_id INTEGER,
        created_at TEXT NOT NULL,
        reminded_at TEXT,
        deleted_at TEXT,
        delete_reason TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cases (
        case_id TEXT PRIMARY KEY,
        case_number TEXT NOT NULL UNIQUE,
        thread_id INTEGER NOT NULL UNIQUE,
        author_id INTEGER NOT NULL,
        module_code TEXT NOT NULL,
        keyword TEXT NOT NULL,
        ai_content_permission INTEGER NOT NULL CHECK(ai_content_permission IN (0, 1)),
        canonical_title TEXT NOT NULL,
        base_title TEXT NOT NULL,
        status TEXT NOT NULL,
        reopen_count INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        closed_at TEXT,
        last_staff_response_at TEXT,
        initial_snapshot_json TEXT NOT NULL,
        dump_version INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS private_support (
        channel_id INTEGER PRIMARY KEY,
        case_number TEXT UNIQUE,
        requester_id INTEGER NOT NULL,
        ai_content_permission INTEGER NOT NULL CHECK(ai_content_permission IN (0, 1)),
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        closed_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS private_dump_jobs (
        channel_id INTEGER PRIMARY KEY,
        status TEXT NOT NULL,
        requested_by INTEGER NOT NULL,
        requested_at TEXT NOT NULL,
        completed_at TEXT,
        manifest_path TEXT,
        delete_completed_at TEXT,
        error TEXT
    )
    """,
)


def _apply_baseline(connection: sqlite3.Connection) -> None:
    for statement in BASELINE_STATEMENTS:
        connection.execute(statement)


def _column_names(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def _apply_legacy_compatibility(connection: sqlite3.Connection) -> None:
    if "base_title" not in _column_names(connection, "cases"):
        connection.execute("ALTER TABLE cases ADD COLUMN base_title TEXT NOT NULL DEFAULT ''")
        rows = connection.execute(
            "SELECT case_id, canonical_title, initial_snapshot_json FROM cases"
        ).fetchall()
        for row in rows:
            base_title = str(row[1])
            try:
                snapshot = json.loads(str(row[2]))
                snapshot_title = snapshot.get("title")
                if isinstance(snapshot_title, str) and snapshot_title.strip():
                    base_title = snapshot_title
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
            connection.execute(
                "UPDATE cases SET base_title = ? WHERE case_id = ?",
                (base_title, str(row[0])),
            )

    if "case_number" not in _column_names(connection, "private_support"):
        connection.execute("ALTER TABLE private_support ADD COLUMN case_number TEXT")
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS private_support_case_number_unique
        ON private_support(case_number)
        """
    )


def _apply_private_dump_job_leases(connection: sqlite3.Connection) -> None:
    columns = _column_names(connection, "private_dump_jobs")
    additions = (
        ("claim_token", "TEXT"),
        ("claimed_by", "TEXT"),
        ("lease_expires_at", "TEXT"),
        ("attempt_count", "INTEGER NOT NULL DEFAULT 0"),
        ("retry_at", "TEXT"),
        ("failure_kind", "TEXT"),
        ("updated_at", "TEXT"),
    )
    for name, declaration in additions:
        if name not in columns:
            connection.execute(f"ALTER TABLE private_dump_jobs ADD COLUMN {name} {declaration}")
    connection.execute(
        """
        UPDATE private_dump_jobs
        SET updated_at = COALESCE(updated_at, completed_at, requested_at),
            attempt_count = CASE
                WHEN status IN ('VERIFIED', 'DELETED') AND attempt_count = 0 THEN 1
                ELSE attempt_count
            END
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS private_dump_jobs_claimable
        ON private_dump_jobs(status, retry_at, lease_expires_at, requested_at)
        """
    )


PHASE2B_BRIDGE_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS case_lifecycle_events (
        event_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        case_ref TEXT NOT NULL CHECK(case_ref LIKE 'TST-%'),
        event_type TEXT NOT NULL CHECK(event_type IN ('OPEN', 'CLOSE', 'REOPEN')),
        previous_status TEXT,
        new_status TEXT NOT NULL,
        source_kind TEXT NOT NULL CHECK(source_kind IN ('LOCAL_FIXTURE', 'CLOUD_COMMAND')),
        correlation_id TEXT NOT NULL,
        occurred_at TEXT NOT NULL,
        synthetic INTEGER NOT NULL CHECK(synthetic IN (0, 1) AND synthetic = 1)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS case_lifecycle_events_case_time
    ON case_lifecycle_events(case_ref, occurred_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS inbound_commands (
        command_id TEXT PRIMARY KEY CHECK(command_id LIKE 'CMD-TST-%'),
        idempotency_key TEXT NOT NULL UNIQUE,
        command_type TEXT NOT NULL CHECK(command_type IN (
            'CREATE_SYNTHETIC_CASE',
            'CLOSE_SYNTHETIC_CASE',
            'REOPEN_SYNTHETIC_CASE',
            'REPLAY_LAST_SYNTHETIC_COMMAND'
        )),
        payload_ref TEXT NOT NULL CHECK(payload_ref IN (
            'fixture://public/basic-v1',
            'fixture://public/close-reopen-v1',
            'fixture://failure/stale-version-v1',
            'fixture://failure/bad-checksum-v1'
        )),
        target_case_ref TEXT,
        source_version INTEGER NOT NULL CHECK(source_version > 0),
        envelope_sha256 TEXT NOT NULL CHECK(
            length(envelope_sha256) = 64
            AND envelope_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
        source_fingerprint TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('FETCHED', 'VALIDATED', 'APPLIED', 'REJECTED')),
        fetched_at TEXT NOT NULL,
        validated_at TEXT,
        applied_at TEXT,
        rejected_at TEXT,
        result_code TEXT,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS projection_outbox (
        projection_id TEXT PRIMARY KEY,
        aggregate_type TEXT NOT NULL CHECK(aggregate_type IN ('PUBLIC_CASE', 'OPERATIONS')),
        aggregate_ref TEXT NOT NULL,
        event_type TEXT NOT NULL CHECK(event_type IN (
            'UPSERT_CURRENT_STATE', 'APPEND_HISTORY', 'UPDATE_OPERATIONS'
        )),
        projection_scope TEXT NOT NULL CHECK(projection_scope IN (
            'OVERVIEW', 'CASEBOARD', 'HISTORY', 'OPERATIONS'
        )),
        source_version INTEGER NOT NULL CHECK(source_version > 0),
        payload_sha256 TEXT CHECK(
            payload_sha256 IS NULL OR (
                length(payload_sha256) = 64
                AND payload_sha256 NOT GLOB '*[^0-9a-f]*'
            )
        ),
        status TEXT NOT NULL CHECK(status IN (
            'PENDING', 'CLAIMED', 'COMPLETED', 'RETRYABLE_FAILURE', 'PERMANENT_FAILURE'
        )),
        attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
        next_attempt_at TEXT,
        claimed_by TEXT,
        claim_token TEXT,
        lease_expires_at TEXT,
        last_error_code TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        completed_at TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS projection_outbox_claimable
    ON projection_outbox(status, next_attempt_at, lease_expires_at, created_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS projection_outbox_current_state
    ON projection_outbox(aggregate_ref, projection_scope, source_version)
    """,
    """
    CREATE TABLE IF NOT EXISTS sync_state (
        stream_name TEXT PRIMARY KEY,
        last_remote_source_version INTEGER NOT NULL DEFAULT 0,
        last_remote_checksum TEXT,
        last_local_projection_version INTEGER NOT NULL DEFAULT 0,
        last_local_projection_checksum TEXT,
        last_success_at TEXT,
        receipt_ref TEXT,
        updated_at TEXT NOT NULL
    )
    """,
)


def _apply_phase2b_data_bridge(connection: sqlite3.Connection) -> None:
    for statement in PHASE2B_BRIDGE_STATEMENTS:
        connection.execute(statement)
    now = utc_now_iso()
    for stream_name in ("cloud-command-inbox", "local-sheet-projection"):
        connection.execute(
            """
            INSERT OR IGNORE INTO sync_state(stream_name, updated_at)
            VALUES (?, ?)
            """,
            (stream_name, now),
        )


PHASE2C_PRODUCTION_STATEMENTS = (
    """
    CREATE TABLE case_lifecycle_events_v5 (
        event_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        case_ref TEXT NOT NULL,
        event_type TEXT NOT NULL CHECK(event_type IN ('OPEN', 'CLOSE', 'REOPEN')),
        previous_status TEXT,
        new_status TEXT NOT NULL,
        source_kind TEXT NOT NULL CHECK(source_kind IN (
            'LOCAL_FIXTURE', 'CLOUD_COMMAND', 'DISCORD'
        )),
        correlation_id TEXT NOT NULL,
        occurred_at TEXT NOT NULL,
        synthetic INTEGER NOT NULL CHECK(synthetic IN (0, 1))
    )
    """,
    """
    INSERT INTO case_lifecycle_events_v5(
        event_id, case_id, case_ref, event_type, previous_status, new_status,
        source_kind, correlation_id, occurred_at, synthetic
    )
    SELECT event_id, case_id, case_ref, event_type, previous_status, new_status,
           source_kind, correlation_id, occurred_at, synthetic
    FROM case_lifecycle_events
    """,
    "DROP TABLE case_lifecycle_events",
    "ALTER TABLE case_lifecycle_events_v5 RENAME TO case_lifecycle_events",
    """
    CREATE INDEX case_lifecycle_events_case_time
    ON case_lifecycle_events(case_ref, occurred_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS service_health (
        service_key TEXT PRIMARY KEY,
        service TEXT NOT NULL,
        component TEXT NOT NULL,
        status TEXT NOT NULL,
        mode TEXT NOT NULL,
        version TEXT,
        last_heartbeat_at TEXT,
        queue_depth INTEGER,
        last_success_at TEXT,
        safe_error_code TEXT,
        next_action TEXT,
        checked_at TEXT NOT NULL
    )
    """,
)


def _apply_phase2c_production_bridge(connection: sqlite3.Connection) -> None:
    for statement in PHASE2C_PRODUCTION_STATEMENTS:
        connection.execute(statement)
    now = utc_now_iso()
    connection.execute(
        """
        INSERT OR IGNORE INTO sync_state(stream_name, updated_at)
        VALUES ('production-local-sheet-projection', ?)
        """,
        (now,),
    )


LIFECYCLE_JOB_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS discord_lifecycle_jobs (
        job_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        thread_id INTEGER NOT NULL,
        transition TEXT NOT NULL CHECK(transition IN ('CLOSE', 'REOPEN')),
        cycle_number INTEGER NOT NULL CHECK(cycle_number > 0),
        desired_title TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN (
            'PENDING', 'CLAIMED', 'COMPLETED',
            'RETRYABLE_FAILURE', 'PERMANENT_FAILURE'
        )),
        stage TEXT NOT NULL CHECK(stage IN (
            'PENDING', 'NOTICE_SENT', 'DISCORD_APPLIED'
        )),
        control_message_id INTEGER,
        attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
        next_attempt_at TEXT,
        claimed_by TEXT,
        claim_token TEXT,
        lease_expires_at TEXT,
        last_error_code TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        completed_at TEXT,
        UNIQUE(case_id, transition, cycle_number)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS discord_lifecycle_jobs_claimable
    ON discord_lifecycle_jobs(status, next_attempt_at, lease_expires_at, created_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS discord_lifecycle_jobs_case_cycle
    ON discord_lifecycle_jobs(case_id, cycle_number, created_at)
    """,
)


def _apply_discord_lifecycle_jobs(connection: sqlite3.Connection) -> None:
    for statement in LIFECYCLE_JOB_STATEMENTS:
        connection.execute(statement)


CASE_RUNTIME_V7_STATEMENTS = (
    """
    CREATE TABLE case_lifecycle_events_v7 (
        event_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        case_ref TEXT NOT NULL,
        event_type TEXT NOT NULL CHECK(event_type IN (
            'OPEN', 'TRACK', 'ACTIVITY', 'IDLE', 'CLOSE', 'AUTO_CLOSE', 'REOPEN'
        )),
        previous_status TEXT,
        new_status TEXT NOT NULL,
        source_kind TEXT NOT NULL CHECK(source_kind IN (
            'LOCAL_FIXTURE', 'CLOUD_COMMAND', 'DISCORD', 'SCHEDULER'
        )),
        correlation_id TEXT NOT NULL,
        occurred_at TEXT NOT NULL,
        synthetic INTEGER NOT NULL CHECK(synthetic IN (0, 1))
    )
    """,
    """
    INSERT INTO case_lifecycle_events_v7(
        event_id, case_id, case_ref, event_type, previous_status, new_status,
        source_kind, correlation_id, occurred_at, synthetic
    )
    SELECT event_id, case_id, case_ref, event_type, previous_status, new_status,
           source_kind, correlation_id, occurred_at, synthetic
    FROM case_lifecycle_events
    """,
    "DROP TABLE case_lifecycle_events",
    "ALTER TABLE case_lifecycle_events_v7 RENAME TO case_lifecycle_events",
    """
    CREATE INDEX case_lifecycle_events_case_time
    ON case_lifecycle_events(case_ref, occurred_at)
    """,
    """
    CREATE TABLE discord_lifecycle_jobs_v7 (
        job_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        thread_id INTEGER NOT NULL,
        transition TEXT NOT NULL CHECK(transition IN (
            'IDLE', 'CLOSE', 'AUTO_CLOSE', 'REOPEN'
        )),
        cycle_number INTEGER NOT NULL CHECK(cycle_number > 0),
        desired_title TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN (
            'PENDING', 'CLAIMED', 'COMPLETED',
            'RETRYABLE_FAILURE', 'PERMANENT_FAILURE'
        )),
        stage TEXT NOT NULL CHECK(stage IN (
            'PENDING', 'NOTICE_SENT', 'DISCORD_APPLIED'
        )),
        control_message_id INTEGER,
        attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
        next_attempt_at TEXT,
        claimed_by TEXT,
        claim_token TEXT,
        lease_expires_at TEXT,
        last_error_code TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        completed_at TEXT,
        UNIQUE(case_id, transition, cycle_number)
    )
    """,
    """
    INSERT INTO discord_lifecycle_jobs_v7(
        job_id, case_id, thread_id, transition, cycle_number, desired_title,
        status, stage, control_message_id, attempt_count, next_attempt_at,
        claimed_by, claim_token, lease_expires_at, last_error_code,
        created_at, updated_at, completed_at
    )
    SELECT job_id, case_id, thread_id, transition, cycle_number, desired_title,
           status, stage, control_message_id, attempt_count, next_attempt_at,
           claimed_by, claim_token, lease_expires_at, last_error_code,
           created_at, updated_at, completed_at
    FROM discord_lifecycle_jobs
    """,
    "DROP TABLE discord_lifecycle_jobs",
    "ALTER TABLE discord_lifecycle_jobs_v7 RENAME TO discord_lifecycle_jobs",
    """
    CREATE INDEX discord_lifecycle_jobs_claimable
    ON discord_lifecycle_jobs(status, next_attempt_at, lease_expires_at, created_at)
    """,
    """
    CREATE INDEX discord_lifecycle_jobs_case_cycle
    ON discord_lifecycle_jobs(case_id, cycle_number, created_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS private_open_requests (
        interaction_id TEXT PRIMARY KEY,
        idempotency_key TEXT NOT NULL UNIQUE,
        guild_id INTEGER NOT NULL,
        requester_id INTEGER NOT NULL,
        ai_content_permission INTEGER NOT NULL CHECK(ai_content_permission IN (0, 1)),
        status TEXT NOT NULL CHECK(status IN (
            'PENDING', 'CLAIMED', 'COMPLETED', 'REJECTED',
            'RETRYABLE_FAILURE', 'PERMANENT_FAILURE'
        )),
        channel_id INTEGER,
        case_id TEXT,
        case_number TEXT,
        jump_url TEXT,
        rejection_code TEXT,
        attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
        next_attempt_at TEXT,
        claimed_by TEXT,
        claim_token TEXT,
        lease_expires_at TEXT,
        last_error_code TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        completed_at TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS private_open_requests_claimable
    ON private_open_requests(status, next_attempt_at, lease_expires_at, created_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS private_open_requests_requester_time
    ON private_open_requests(requester_id, created_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS discord_dm_outbox (
        message_key TEXT PRIMARY KEY,
        recipient_id INTEGER NOT NULL,
        message_kind TEXT NOT NULL,
        aggregate_ref TEXT NOT NULL,
        body TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN (
            'PENDING', 'CLAIMED', 'COMPLETED',
            'RETRYABLE_FAILURE', 'PERMANENT_FAILURE'
        )),
        attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
        next_attempt_at TEXT,
        claimed_by TEXT,
        claim_token TEXT,
        lease_expires_at TEXT,
        last_error_code TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        completed_at TEXT,
        UNIQUE(message_kind, aggregate_ref, recipient_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS discord_dm_outbox_claimable
    ON discord_dm_outbox(status, next_attempt_at, lease_expires_at, created_at)
    """,
)


def _apply_case_runtime_v7(connection: sqlite3.Connection) -> None:
    case_columns = _column_names(connection, "cases")
    additions = (
        ("visibility", "TEXT NOT NULL DEFAULT 'PUBLIC'"),
        ("assigned_staff_id", "INTEGER"),
        ("last_student_activity_at", "TEXT"),
        ("idle_at", "TEXT"),
        ("idle_reminded_at", "TEXT"),
        ("updated_at", "TEXT"),
        ("teaching_team_replied", "INTEGER NOT NULL DEFAULT 0"),
        ("jump_url", "TEXT"),
    )
    for name, declaration in additions:
        if name not in case_columns:
            connection.execute(f"ALTER TABLE cases ADD COLUMN {name} {declaration}")
    connection.execute(
        """
        UPDATE cases
        SET last_student_activity_at = COALESCE(last_student_activity_at, created_at),
            updated_at = COALESCE(updated_at, closed_at, created_at)
        """
    )
    private_columns = _column_names(connection, "private_support")
    for name, declaration in (
        ("case_id", "TEXT"),
        ("interaction_id", "TEXT"),
        ("updated_at", "TEXT"),
    ):
        if name not in private_columns:
            connection.execute(f"ALTER TABLE private_support ADD COLUMN {name} {declaration}")
    for statement in CASE_RUNTIME_V7_STATEMENTS:
        connection.execute(statement)


JOIN_REVIEW_V8_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS join_applications (
        application_id TEXT PRIMARY KEY,
        identity_key TEXT NOT NULL UNIQUE,
        applicant_type TEXT NOT NULL CHECK(applicant_type IN ('STUDENT', 'VISITOR')),
        discord_username TEXT NOT NULL,
        normalized_username TEXT NOT NULL,
        identity_email TEXT NOT NULL,
        normalized_email TEXT NOT NULL,
        ntu_mail TEXT,
        contact_email TEXT,
        class_code TEXT,
        visit_reason TEXT,
        discord_user_id INTEGER,
        status TEXT NOT NULL CHECK(status IN (
            'PENDING_REVIEW', 'WAITING_FOR_DISCORD_MEMBER', 'APPROVED',
            'REJECTED', 'ARCHIVED'
        )),
        role_summary TEXT,
        previous_status TEXT,
        archive_reason TEXT,
        archived_by INTEGER,
        archived_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS join_applications_discord_user_unique
    ON join_applications(discord_user_id) WHERE discord_user_id IS NOT NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS join_applications_review_queue
    ON join_applications(status, created_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS join_application_events (
        event_id TEXT PRIMARY KEY,
        application_id TEXT NOT NULL,
        previous_status TEXT,
        new_status TEXT NOT NULL,
        actor_id INTEGER,
        reason_code TEXT,
        occurred_at TEXT NOT NULL,
        FOREIGN KEY(application_id) REFERENCES join_applications(application_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS join_application_events_time
    ON join_application_events(application_id, occurred_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS reviewer_grants (
        discord_user_id INTEGER PRIMARY KEY,
        reviewer_level TEXT NOT NULL CHECK(reviewer_level IN ('REVIEWER', 'SYSTEM_ADMIN')),
        active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
        granted_by INTEGER NOT NULL,
        granted_at TEXT NOT NULL,
        revoked_by INTEGER,
        revoked_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS course_role_jobs (
        job_id TEXT PRIMARY KEY,
        application_id TEXT NOT NULL UNIQUE,
        discord_user_id INTEGER NOT NULL,
        desired_roles_json TEXT NOT NULL,
        desired_nickname TEXT,
        status TEXT NOT NULL CHECK(status IN (
            'PENDING', 'CLAIMED', 'COMPLETED',
            'RETRYABLE_FAILURE', 'PERMANENT_FAILURE'
        )),
        attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
        next_attempt_at TEXT,
        claimed_by TEXT,
        claim_token TEXT,
        lease_expires_at TEXT,
        last_error_code TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        completed_at TEXT,
        FOREIGN KEY(application_id) REFERENCES join_applications(application_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS course_role_jobs_claimable
    ON course_role_jobs(status, next_attempt_at, lease_expires_at, created_at)
    """,
)


def _apply_join_review_v8(connection: sqlite3.Connection) -> None:
    for statement in JOIN_REVIEW_V8_STATEMENTS:
        connection.execute(statement)


COURSE_ALIAS_V9_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS course_alias_allocations (
        application_id TEXT PRIMARY KEY,
        scope_key TEXT NOT NULL,
        sequence INTEGER NOT NULL CHECK(sequence > 0),
        nickname TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL,
        UNIQUE(scope_key, sequence),
        FOREIGN KEY(application_id) REFERENCES join_applications(application_id)
    )
    """,
)


def _apply_course_alias_v9(connection: sqlite3.Connection) -> None:
    for statement in COURSE_ALIAS_V9_STATEMENTS:
        connection.execute(statement)


def _apply_private_case_setup_v10(connection: sqlite3.Connection) -> None:
    columns = _column_names(connection, "private_open_requests")
    if "module_code" not in columns:
        connection.execute(
            "ALTER TABLE private_open_requests ADD COLUMN module_code TEXT NOT NULL DEFAULT 'M1'"
        )
    if "keyword" not in columns:
        connection.execute(
            "ALTER TABLE private_open_requests ADD COLUMN keyword TEXT NOT NULL DEFAULT '隱密支援'"
        )


EMAIL_DELIVERY_OUTBOX_V11_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS email_delivery_outbox (
        delivery_id TEXT PRIMARY KEY,
        challenge_id TEXT NOT NULL,
        destination TEXT,
        destination_hash TEXT NOT NULL,
        verification_code TEXT,
        email_kind TEXT NOT NULL CHECK(email_kind IN ('INSTITUTIONAL', 'CONTACT')),
        expires_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN (
            'PENDING', 'CLAIMED', 'RETRYABLE_FAILURE', 'COMPLETED', 'PERMANENT_FAILURE'
        )),
        claim_token TEXT,
        claimed_by TEXT,
        lease_expires_at TEXT,
        attempt_count INTEGER NOT NULL DEFAULT 0,
        next_attempt_at TEXT,
        last_error_code TEXT,
        provider_receipt TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(challenge_id, delivery_id),
        CHECK(verification_code IS NULL OR (
            length(verification_code) = 6 AND verification_code NOT GLOB '*[^0-9]*'
        )),
        CHECK(
            status NOT IN ('PENDING', 'CLAIMED', 'RETRYABLE_FAILURE')
            OR (destination IS NOT NULL AND verification_code IS NOT NULL)
        )
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS email_delivery_outbox_claimable
    ON email_delivery_outbox(status, next_attempt_at, lease_expires_at, created_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS email_delivery_outbox_challenge
    ON email_delivery_outbox(challenge_id, created_at)
    """,
)


def _apply_email_delivery_outbox_v11(connection: sqlite3.Connection) -> None:
    for statement in EMAIL_DELIVERY_OUTBOX_V11_STATEMENTS:
        connection.execute(statement)


EMAIL_VERIFICATION_V12_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS email_verification_challenges (
        challenge_id TEXT PRIMARY KEY,
        session_fingerprint TEXT NOT NULL,
        destination_hash TEXT NOT NULL,
        email_kind TEXT NOT NULL CHECK(email_kind IN ('INSTITUTIONAL', 'CONTACT')),
        code_salt TEXT NOT NULL,
        code_hash TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN (
            'PENDING', 'VERIFIED', 'CONSUMED', 'EXPIRED', 'LOCKED'
        )),
        attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count >= 0),
        verified_at TEXT,
        consumed_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS email_verification_session_status
    ON email_verification_challenges(session_fingerprint, status, expires_at)
    """,
)


def _apply_email_verification_v12(connection: sqlite3.Connection) -> None:
    for statement in EMAIL_VERIFICATION_V12_STATEMENTS:
        connection.execute(statement)


MANUAL_ATTENTION_V13_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS manual_attention_actions (
        action_id TEXT PRIMARY KEY,
        queue_kind TEXT NOT NULL,
        item_key TEXT NOT NULL,
        action TEXT NOT NULL CHECK(action IN ('RETRY', 'RESOLVE', 'REPLACEMENT_CASE')),
        actor_id INTEGER NOT NULL,
        reason_code TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS manual_attention_item_time
    ON manual_attention_actions(queue_kind, item_key, created_at)
    """,
)


def _apply_manual_attention_v13(connection: sqlite3.Connection) -> None:
    columns = _column_names(connection, "private_open_requests")
    if "replacement_for_case_id" not in columns:
        connection.execute(
            "ALTER TABLE private_open_requests ADD COLUMN replacement_for_case_id TEXT"
        )
    for statement in MANUAL_ATTENTION_V13_STATEMENTS:
        connection.execute(statement)


MIGRATIONS = (
    Migration(
        1,
        "baseline-five-runtime-tables",
        "\n".join(statement.strip() for statement in BASELINE_STATEMENTS),
        _apply_baseline,
    ),
    Migration(
        2,
        "legacy-base-title-and-private-case-number",
        "cases.base_title from initial snapshot; private_support.case_number; unique index; v1",
        _apply_legacy_compatibility,
    ),
    Migration(
        3,
        "private-dump-job-claim-lease-retry",
        (
            "private_dump_jobs claim_token claimed_by lease_expires_at attempt_count retry_at "
            "failure_kind updated_at; claimable index; legacy backfill; v1"
        ),
        _apply_private_dump_job_leases,
    ),
    Migration(
        4,
        "phase2b-glassbox-data-bridge",
        "\n".join(statement.strip() for statement in PHASE2B_BRIDGE_STATEMENTS)
        + "\nfixed sync streams cloud-command-inbox local-sheet-projection; v1",
        _apply_phase2b_data_bridge,
    ),
    Migration(
        5,
        "phase2c-production-events-health-and-projection-stream",
        "\n".join(statement.strip() for statement in PHASE2C_PRODUCTION_STATEMENTS)
        + "\nproduction-local-sheet-projection stream; v1",
        _apply_phase2c_production_bridge,
    ),
    Migration(
        6,
        "durable-discord-case-lifecycle-jobs",
        "\n".join(statement.strip() for statement in LIFECYCLE_JOB_STATEMENTS) + "\nv1",
        _apply_discord_lifecycle_jobs,
    ),
    Migration(
        7,
        "portal-contract-case-runtime-v7",
        "\n".join(statement.strip() for statement in CASE_RUNTIME_V7_STATEMENTS)
        + "\ncases visibility assignment activity idle projection fields; "
        "private_support case linkage; v1",
        _apply_case_runtime_v7,
    ),
    Migration(
        8,
        "course-manager-join-review-v8",
        "\n".join(statement.strip() for statement in JOIN_REVIEW_V8_STATEMENTS) + "\nv1",
        _apply_join_review_v8,
    ),
    Migration(
        9,
        "course-manager-safe-nickname-allocation-v9",
        "\n".join(statement.strip() for statement in COURSE_ALIAS_V9_STATEMENTS) + "\nv1",
        _apply_course_alias_v9,
    ),
    Migration(
        10,
        "private-case-shared-setup-v10",
        "private_open_requests module_code and keyword additive columns; v1",
        _apply_private_case_setup_v10,
    ),
    Migration(
        11,
        "durable-email-delivery-outbox-v11",
        "\n".join(statement.strip() for statement in EMAIL_DELIVERY_OUTBOX_V11_STATEMENTS)
        + "\nplaintext delivery fields scrubbed on terminal state; v1",
        _apply_email_delivery_outbox_v11,
    ),
    Migration(
        12,
        "portal-email-verification-challenges-v12",
        "\n".join(statement.strip() for statement in EMAIL_VERIFICATION_V12_STATEMENTS)
        + "\nPBKDF2 code hash; session and destination binding; one-time consumption; v1",
        _apply_email_verification_v12,
    ),
    Migration(
        13,
        "owner-manual-attention-controls-v13",
        "private_open_requests replacement_for_case_id;\n"
        + "\n".join(statement.strip() for statement in MANUAL_ATTENTION_V13_STATEMENTS)
        + "\nallowlisted retry resolve replacement audit; v1",
        _apply_manual_attention_v13,
    ),
)


def _create_ledger(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    connection.commit()


def _verify_recorded_migrations(connection: sqlite3.Connection) -> set[int]:
    known = {migration.version: migration for migration in MIGRATIONS}
    rows = connection.execute(
        "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
    ).fetchall()
    applied: set[int] = set()
    for row in rows:
        version = int(row[0])
        migration = known.get(version)
        if migration is None:
            raise MigrationError(
                f"Database migration {version} is newer than this runtime; refusing downgrade"
            )
        if str(row[1]) != migration.name or str(row[2]) != migration.checksum:
            raise MigrationError(f"Database migration {version} checksum or name does not match")
        applied.add(version)
    return applied


def apply_migrations(connection: sqlite3.Connection) -> None:
    _create_ledger(connection)
    applied = _verify_recorded_migrations(connection)
    for migration in MIGRATIONS:
        if migration.version in applied:
            continue
        try:
            connection.execute("BEGIN IMMEDIATE")
            migration.apply(connection)
            connection.execute(
                """
                INSERT INTO schema_migrations(version, name, checksum, applied_at)
                VALUES (?, ?, ?, ?)
                """,
                (migration.version, migration.name, migration.checksum, utc_now_iso()),
            )
            connection.execute(f"PRAGMA user_version = {migration.version}")
            connection.commit()
        except Exception as error:
            connection.rollback()
            if isinstance(error, MigrationError):
                raise
            raise MigrationError(
                f"Failed to apply migration {migration.version} ({migration.name})"
            ) from error

    expected_version = MIGRATIONS[-1].version
    actual_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if actual_version != expected_version:
        connection.execute(f"PRAGMA user_version = {expected_version}")
        connection.commit()
