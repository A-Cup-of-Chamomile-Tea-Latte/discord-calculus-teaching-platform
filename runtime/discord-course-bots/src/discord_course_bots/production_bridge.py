from __future__ import annotations

import argparse
import json
import logging
import os
import random
import signal
import sys
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from discord_course_bots.apps_script_transport import (
    AppsScriptApiConfig,
    AppsScriptApiError,
    AppsScriptApiTransport,
)
from discord_course_bots.data_lab.commands import fetch_once
from discord_course_bots.data_lab.contracts import validate_common_envelope
from discord_course_bots.data_lab.projection import build_pending_envelope
from discord_course_bots.data_lab.repository import DataLabRepository
from discord_course_bots.repository import Repository
from discord_course_bots.repository_time import utc_now_iso

LOGGER = logging.getLogger("discord_course_bots.production_bridge")


@dataclass(frozen=True, slots=True)
class BridgeSettings:
    database_path: Path
    deployment_id: str
    credential_path: Path
    sheet_fingerprint: str
    environment: str
    synthetic_only: bool
    interval_seconds: int
    staging_lab_root: Path | None

    @classmethod
    def from_environment(cls) -> BridgeSettings:
        environment = os.environ.get("BRIDGE_ENVIRONMENT", "STAGING").strip().upper()
        if environment not in {"STAGING", "PRODUCTION"}:
            raise RuntimeError("BRIDGE_ENVIRONMENT_INVALID")
        synthetic_only = (
            os.environ.get(
                "BRIDGE_SYNTHETIC_ONLY", "1" if environment == "STAGING" else "0"
            ).strip()
            == "1"
        )
        if (environment == "STAGING") is not synthetic_only:
            raise RuntimeError("BRIDGE_MODE_MISMATCH")
        required = {
            "GAS_DEPLOYMENT_ID": os.environ.get("GAS_DEPLOYMENT_ID", "").strip(),
            "GOOGLE_OAUTH_CREDENTIALS": os.environ.get("GOOGLE_OAUTH_CREDENTIALS", "").strip(),
            "SHEET_FINGERPRINT": os.environ.get("SHEET_FINGERPRINT", "").strip(),
            "DATABASE_PATH": os.environ.get("DATABASE_PATH", "").strip(),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(f"BRIDGE_CONFIG_MISSING_{'_'.join(missing)}")
        interval = int(os.environ.get("BRIDGE_INTERVAL_SECONDS", "60"))
        if not 30 <= interval <= 300:
            raise RuntimeError("BRIDGE_INTERVAL_OUT_OF_RANGE")
        root = os.environ.get("STAGING_LAB_ROOT", "").strip()
        return cls(
            database_path=Path(required["DATABASE_PATH"]),
            deployment_id=required["GAS_DEPLOYMENT_ID"],
            credential_path=Path(required["GOOGLE_OAUTH_CREDENTIALS"]),
            sheet_fingerprint=required["SHEET_FINGERPRINT"],
            environment=environment,
            synthetic_only=synthetic_only,
            interval_seconds=interval,
            staging_lab_root=Path(root) if root else None,
        )


def _stream_name(settings: BridgeSettings) -> str:
    return (
        "local-sheet-projection" if settings.synthetic_only else "production-local-sheet-projection"
    )


def _record_health(
    repository: DataLabRepository,
    settings: BridgeSettings,
    *,
    status: str,
    safe_error_code: str | None,
    successful: bool,
    enqueue: bool,
) -> None:
    now = utc_now_iso()
    depth = int(
        repository._connection.execute(  # noqa: SLF001
            "SELECT COUNT(*) FROM projection_outbox WHERE status != 'COMPLETED'"
        ).fetchone()[0]
    )
    with repository.immediate_transaction() as db:
        current = db.execute(
            "SELECT last_success_at, status, safe_error_code FROM service_health "
            "WHERE service_key = 'data-bridge'"
        ).fetchone()
        last_success = now if successful else (None if current is None else current[0])
        changed = (
            current is None or str(current[1]) != status or (current[2] or None) != safe_error_code
        )
        db.execute(
            """
            INSERT INTO service_health(
                service_key, service, component, status, mode, version,
                last_heartbeat_at, queue_depth, last_success_at, safe_error_code,
                next_action, checked_at
            ) VALUES (
                'data-bridge', 'calculus-data-bridge', 'apps-script-api', ?, ?,
                'phase-2c', ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(service_key) DO UPDATE SET
                status=excluded.status, mode=excluded.mode,
                last_heartbeat_at=excluded.last_heartbeat_at,
                queue_depth=excluded.queue_depth,
                last_success_at=excluded.last_success_at,
                safe_error_code=excluded.safe_error_code,
                next_action=excluded.next_action, checked_at=excluded.checked_at
            """,
            (
                status,
                "SYNTHETIC_ONLY" if settings.synthetic_only else "PRODUCTION",
                now,
                depth,
                last_success,
                safe_error_code,
                "check OAuth/network" if safe_error_code else "none",
                now,
            ),
        )
        if not enqueue and not changed:
            return
        stream = _stream_name(settings)
        row = db.execute(
            "SELECT last_local_projection_version FROM sync_state WHERE stream_name = ?",
            (stream,),
        ).fetchone()
        if row is None:
            raise RuntimeError("BRIDGE_SYNC_STREAM_MISSING")
        version = int(row[0]) + 1
        db.execute(
            "UPDATE sync_state SET last_local_projection_version = ?, updated_at = ? "
            "WHERE stream_name = ?",
            (version, now, stream),
        )
        projection_id = f"prj-health-{version}"
        db.execute(
            """
            INSERT OR IGNORE INTO projection_outbox(
                projection_id, aggregate_type, aggregate_ref, event_type,
                projection_scope, source_version, status, created_at, updated_at
            ) VALUES (?, 'OPERATIONS', 'data-bridge', 'UPDATE_OPERATIONS',
                      'OPERATIONS', ?, 'PENDING', ?, ?)
            """,
            (projection_id, version, now, now),
        )


def project_once(
    settings: BridgeSettings,
    transport: AppsScriptApiTransport,
    *,
    apply: bool,
) -> dict[str, Any]:
    repository = DataLabRepository(settings.database_path)
    try:
        envelope, pending_ids = build_pending_envelope(
            repository,
            settings.sheet_fingerprint,
            environment=settings.environment,
            synthetic_only=settings.synthetic_only,
        )
        if envelope is None:
            return {"status": "NO_WORK", "safeResultCode": "PROJECTION_QUEUE_EMPTY"}
        validate_common_envelope(
            envelope,
            settings.sheet_fingerprint,
            expected_environment=settings.environment,
            expected_synthetic_only=settings.synthetic_only,
        )
        preview = transport.preview(envelope)
        result = {
            **asdict(preview),
            "pendingWorkCount": len(pending_ids),
            "dryRun": not apply,
            "cloudMutation": False,
            "transport": transport.transport_name,
        }
        if not apply:
            return result
        receipt = transport.apply(envelope, preview.confirmation_nonce)
        claims = []
        for _ in pending_ids:
            claim = repository.claim_projection(worker_id="phase2c-bridge")
            if claim is None:
                raise RuntimeError("PROJECTION_CLAIM_INCOMPLETE")
            claims.append(claim)
        for claim in claims:
            if not repository.complete_projection(
                str(claim.key), claim.claim_token, envelope["checksum"]
            ):
                raise RuntimeError("PROJECTION_COMPLETION_FAILED")
        now = utc_now_iso()
        with repository.transaction() as db:
            db.execute(
                """
                UPDATE sync_state SET last_local_projection_checksum = ?,
                    last_success_at = ?, receipt_ref = ?, updated_at = ?
                WHERE stream_name = ?
                """,
                (
                    envelope["checksum"],
                    now,
                    f"projection-v{envelope['sourceVersion']}",
                    now,
                    _stream_name(settings),
                ),
            )
        return {
            **asdict(receipt),
            "completedWorkCount": len(claims),
            "dryRun": False,
            "cloudMutation": True,
            "transport": transport.transport_name,
        }
    finally:
        repository.close()


RETRYABLE_EMAIL_ERRORS = frozenset(
    {
        "EMAIL_QUOTA_RESERVED",
        "GOOGLE_RATE_LIMITED",
        "GOOGLE_TRANSPORT_UNAVAILABLE",
        "OAUTH_REFRESH_FAILED",
    }
)


def deliver_verification_email_once(
    settings: BridgeSettings,
    transport: AppsScriptApiTransport,
) -> dict[str, Any]:
    repository = Repository(settings.database_path)
    try:
        claim = repository.claim_verification_email("production-email-bridge")
        if claim is None:
            return {"status": "NO_WORK", "safeResultCode": "EMAIL_QUEUE_EMPTY"}
        try:
            receipt = transport.send_verification_email(
                {
                    "deliveryId": claim.delivery_id,
                    "challengeId": claim.challenge_id,
                    "destination": claim.destination,
                    "code": claim.verification_code,
                    "kind": claim.email_kind,
                    "expiresAt": claim.expires_at,
                }
            )
            if str(receipt.get("deliveryId")) != claim.delivery_id:
                raise AppsScriptApiError("EMAIL_DELIVERY_RECEIPT_MISMATCH")
            safe_result = str(receipt["safeResultCode"])
            if not repository.complete_verification_email(
                claim.delivery_id, claim.claim_token, safe_result
            ):
                raise RuntimeError("EMAIL_DELIVERY_COMPLETION_FAILED")
            return {"status": "COMPLETED", "safeResultCode": safe_result}
        except AppsScriptApiError as error:
            retryable = error.code in RETRYABLE_EMAIL_ERRORS or error.code.startswith(
                "GOOGLE_HTTP_5"
            )
            repository.fail_verification_email(
                claim.delivery_id,
                claim.claim_token,
                error_code=error.code,
                retryable=retryable,
            )
            return {
                "status": "RETRYABLE_FAILURE" if retryable else "PERMANENT_FAILURE",
                "safeResultCode": error.code,
            }
    finally:
        repository.close()


class BridgeDaemon:
    def __init__(self, settings: BridgeSettings, transport: AppsScriptApiTransport) -> None:
        self.settings = settings
        self.transport = transport
        self.stop = threading.Event()
        self._cycles = 0

    def request_stop(self, *_: Any) -> None:
        self.stop.set()

    def cycle(self) -> dict[str, Any]:
        repository = DataLabRepository(self.settings.database_path)
        try:
            _record_health(
                repository,
                self.settings,
                status="HEALTHY",
                safe_error_code=None,
                successful=True,
                enqueue=self._cycles % 5 == 0,
            )
        finally:
            repository.close()
        projection = project_once(self.settings, self.transport, apply=True)
        email = deliver_verification_email_once(self.settings, self.transport)
        command: dict[str, Any] = {
            "status": "DISABLED",
            "safeResultCode": "PRODUCTION_COMMANDS_OUT_OF_SCOPE",
        }
        if self.settings.synthetic_only and self.settings.staging_lab_root is not None:
            preview = fetch_once(self.settings.staging_lab_root, self.transport, apply=False)
            command = preview
            if preview.get("status") == "PREVIEW":
                command = fetch_once(
                    self.settings.staging_lab_root,
                    self.transport,
                    apply=True,
                    confirmation_nonce=str(preview["confirmationNonce"]),
                )
                if int(projection.get("pendingWorkCount", 0)) >= 20:
                    projection = project_once(self.settings, self.transport, apply=True)
        self._cycles += 1
        return {"projection": projection, "email": email, "command": command}

    def run(self) -> None:
        self.transport.health()
        while not self.stop.is_set():
            try:
                result = self.cycle()
                LOGGER.info(
                    "bridge cycle completed projection=%s email=%s command=%s",
                    result["projection"].get("safeResultCode"),
                    result["email"].get("safeResultCode"),
                    result["command"].get("safeResultCode"),
                )
            except Exception as error:
                code = (
                    error.code if isinstance(error, AppsScriptApiError) else "BRIDGE_CYCLE_FAILED"
                )
                LOGGER.error("bridge cycle degraded code=%s", code)
                repository = DataLabRepository(self.settings.database_path)
                try:
                    _record_health(
                        repository,
                        self.settings,
                        status="DEGRADED",
                        safe_error_code=code,
                        successful=False,
                        enqueue=True,
                    )
                finally:
                    repository.close()
            wait = self.settings.interval_seconds + random.uniform(-3, 3)
            self.stop.wait(max(5, wait))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Phase 2C production GAS/SQLite bridge")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("health")
    once = commands.add_parser("once")
    once.add_argument("--dry-run", action="store_true")
    commands.add_parser("daemon")
    return result


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = parser().parse_args()
    settings = BridgeSettings.from_environment()
    transport = AppsScriptApiTransport(
        AppsScriptApiConfig(settings.deployment_id, settings.credential_path)
    )
    try:
        if args.command == "health":
            print(json.dumps(transport.health(), ensure_ascii=False, sort_keys=True))
            return
        if args.command == "once":
            projection = project_once(settings, transport, apply=not args.dry_run)
            email = (
                {"status": "DRY_RUN", "safeResultCode": "EMAIL_DELIVERY_NOT_ATTEMPTED"}
                if args.dry_run
                else deliver_verification_email_once(settings, transport)
            )
            print(
                json.dumps(
                    {"projection": projection, "email": email},
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return
    except AppsScriptApiError as error:
        print(
            json.dumps(
                {"status": "ERROR", "safeResultCode": error.code},
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    daemon = BridgeDaemon(settings, transport)
    signal.signal(signal.SIGTERM, daemon.request_stop)
    signal.signal(signal.SIGINT, daemon.request_stop)
    daemon.run()


if __name__ == "__main__":
    main()
