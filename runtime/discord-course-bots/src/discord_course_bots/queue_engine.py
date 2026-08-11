from __future__ import annotations

import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

SAFE_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class ReliableQueueSpec:
    table: str
    key_column: str
    retry_column: str
    error_column: str
    order_column: str
    retry_status: str
    terminal_failure_status: str
    reset_columns_on_claim: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for identifier in (
            self.table,
            self.key_column,
            self.retry_column,
            self.error_column,
            self.order_column,
            *self.reset_columns_on_claim,
        ):
            if not SAFE_IDENTIFIER.fullmatch(identifier):
                raise ValueError("Unsafe queue identifier")


@dataclass(frozen=True, slots=True)
class QueueClaim:
    key: Any
    claim_token: str
    claimed_by: str
    attempt_count: int
    lease_expires_at: str


@dataclass(frozen=True, slots=True)
class QueueFailure:
    key: Any
    status: str
    attempt_count: int
    retry_at: str | None
    exhausted: bool


def normalized_moment(now: datetime | None) -> datetime:
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return moment.astimezone(UTC)


def claim_next(
    connection: sqlite3.Connection,
    spec: ReliableQueueSpec,
    *,
    worker_id: str,
    now: datetime | None = None,
    lease_seconds: int = 900,
) -> QueueClaim | None:
    worker = worker_id.strip()
    if not worker or len(worker) > 128:
        raise ValueError("worker_id must contain 1–128 characters")
    if lease_seconds <= 0:
        raise ValueError("lease_seconds must be positive")
    moment = normalized_moment(now)
    now_iso = moment.isoformat()
    lease_expires_at = (moment + timedelta(seconds=lease_seconds)).isoformat()
    claim_token = uuid.uuid4().hex
    candidate = connection.execute(
        f"""
        SELECT {spec.key_column}
        FROM {spec.table}
        WHERE (
            status IN ('PENDING', 'RETRYABLE_FAILURE')
            AND ({spec.retry_column} IS NULL OR {spec.retry_column} <= ?)
        ) OR (
            status = 'CLAIMED'
            AND lease_expires_at IS NOT NULL
            AND lease_expires_at <= ?
        )
        ORDER BY COALESCE({spec.retry_column}, {spec.order_column}), {spec.order_column}
        LIMIT 1
        """,
        (now_iso, now_iso),
    ).fetchone()
    if candidate is None:
        return None
    key = candidate[spec.key_column]
    reset_sql = "".join(f", {column} = NULL" for column in spec.reset_columns_on_claim)
    result = connection.execute(
        f"""
        UPDATE {spec.table}
        SET status = 'CLAIMED', claim_token = ?, claimed_by = ?,
            lease_expires_at = ?, attempt_count = attempt_count + 1,
            {spec.retry_column} = NULL, updated_at = ?{reset_sql}
        WHERE {spec.key_column} = ? AND (
            (status IN ('PENDING', 'RETRYABLE_FAILURE')
             AND ({spec.retry_column} IS NULL OR {spec.retry_column} <= ?))
            OR (status = 'CLAIMED' AND lease_expires_at IS NOT NULL
                AND lease_expires_at <= ?)
        )
        """,
        (claim_token, worker, lease_expires_at, now_iso, key, now_iso, now_iso),
    )
    if result.rowcount != 1:
        return None
    row = connection.execute(
        f"SELECT attempt_count FROM {spec.table} WHERE {spec.key_column} = ?", (key,)
    ).fetchone()
    if row is None:
        raise RuntimeError("Claimed queue row disappeared")
    return QueueClaim(key, claim_token, worker, int(row["attempt_count"]), lease_expires_at)


def renew_claim(
    connection: sqlite3.Connection,
    spec: ReliableQueueSpec,
    *,
    key: Any,
    claim_token: str,
    now: datetime | None = None,
    lease_seconds: int = 900,
) -> bool:
    if lease_seconds <= 0:
        raise ValueError("lease_seconds must be positive")
    moment = normalized_moment(now)
    now_iso = moment.isoformat()
    lease_expires_at = (moment + timedelta(seconds=lease_seconds)).isoformat()
    result = connection.execute(
        f"""
        UPDATE {spec.table}
        SET lease_expires_at = ?, updated_at = ?
        WHERE {spec.key_column} = ? AND status = 'CLAIMED' AND claim_token = ?
          AND lease_expires_at > ?
        """,
        (lease_expires_at, now_iso, key, claim_token, now_iso),
    )
    return result.rowcount == 1


def complete_claim(
    connection: sqlite3.Connection,
    spec: ReliableQueueSpec,
    *,
    key: Any,
    claim_token: str,
    final_status: str,
    values: dict[str, Any] | None = None,
) -> bool:
    updates = dict(values or {})
    for identifier in updates:
        if not SAFE_IDENTIFIER.fullmatch(identifier):
            raise ValueError("Unsafe queue completion identifier")
    assignments = [
        "status = ?",
        "claim_token = NULL",
        "claimed_by = NULL",
        "lease_expires_at = NULL",
    ]
    parameters: list[Any] = [final_status]
    for column, value in updates.items():
        assignments.append(f"{column} = ?")
        parameters.append(value)
    parameters.extend((key, claim_token))
    result = connection.execute(
        f"""
        UPDATE {spec.table}
        SET {", ".join(assignments)}
        WHERE {spec.key_column} = ? AND status = 'CLAIMED' AND claim_token = ?
        """,
        parameters,
    )
    return result.rowcount == 1


def fail_claim(
    connection: sqlite3.Connection,
    spec: ReliableQueueSpec,
    *,
    key: Any,
    claim_token: str,
    error_code: str,
    retryable: bool,
    now: datetime | None = None,
    max_attempts: int = 5,
    base_retry_seconds: int = 30,
    max_retry_seconds: int = 1800,
) -> QueueFailure | None:
    if max_attempts <= 0 or base_retry_seconds <= 0 or max_retry_seconds <= 0:
        raise ValueError("retry limits must be positive")
    moment = normalized_moment(now)
    now_iso = moment.isoformat()
    row = connection.execute(
        f"""
        SELECT attempt_count FROM {spec.table}
        WHERE {spec.key_column} = ? AND status = 'CLAIMED' AND claim_token = ?
        """,
        (key, claim_token),
    ).fetchone()
    if row is None:
        return None
    attempt_count = int(row["attempt_count"])
    should_retry = retryable and attempt_count < max_attempts
    if should_retry:
        delay = min(max_retry_seconds, base_retry_seconds * (2 ** (attempt_count - 1)))
        status = spec.retry_status
        retry_at = (moment + timedelta(seconds=delay)).isoformat()
    else:
        status = spec.terminal_failure_status
        retry_at = None
    result = connection.execute(
        f"""
        UPDATE {spec.table}
        SET status = ?, {spec.retry_column} = ?, {spec.error_column} = ?,
            claim_token = NULL, claimed_by = NULL, lease_expires_at = NULL,
            updated_at = ?
        WHERE {spec.key_column} = ? AND status = 'CLAIMED' AND claim_token = ?
        """,
        (status, retry_at, error_code, now_iso, key, claim_token),
    )
    if result.rowcount != 1:
        return None
    return QueueFailure(key, status, attempt_count, retry_at, not should_retry)
