from __future__ import annotations

import getpass
import hashlib
import hmac
import json
import os
import re
import stat
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from .apps_script_transport import AppsScriptApiConfig, AppsScriptApiTransport
from .portal_backend import (
    EMAIL_START_PATH,
    EMAIL_VERIFY_PATH,
    JOIN_CSRF_COOKIE,
    JOIN_PATH,
    SESSION_PATH,
    PortalBackend,
    PortalBackendSettings,
    PortalRequest,
    SignedSessionAuthorizer,
    SQLiteAuditSink,
    SqlitePortalStore,
)
from .production_bridge import BridgeSettings, deliver_verification_email_once

ORIGIN = "https://portal-email-smoke.local"
HOST = "portal-email-smoke.local"
SAFE_USERNAME = re.compile(r"^[A-Za-z0-9._]{2,32}$")


class PortalEmailSmokeError(RuntimeError):
    """A safe, non-secret failure from the controlled real-provider smoke."""


def destination_fingerprint(destination: str) -> str:
    return hashlib.sha256(destination.strip().casefold().encode("utf-8")).hexdigest()


class AllowlistedPortalStore(SqlitePortalStore):
    """Permit exactly one pre-authorized mailbox in an isolated temporary database."""

    def __init__(self, path: Path, allowed_destination_hash: str) -> None:
        super().__init__(path)
        self.allowed_destination_hash = allowed_destination_hash

    def _require_allowed(self, destination: object) -> None:
        if not isinstance(destination, str) or not destination:
            raise ValueError("EMAIL_SMOKE_DESTINATION_REFUSED")
        if not secrets_compare(destination_fingerprint(destination), self.allowed_destination_hash):
            raise ValueError("EMAIL_SMOKE_DESTINATION_REFUSED")

    def start_email_verification(self, **kwargs: Any) -> str:
        self._require_allowed(kwargs.get("destination"))
        return super().start_email_verification(**kwargs)

    def submit_join_application(self, **kwargs: Any) -> tuple[Mapping[str, Any], bool]:
        self._require_allowed(kwargs.get("identity_email"))
        return super().submit_join_application(**kwargs)


def secrets_compare(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)


@dataclass(frozen=True, slots=True)
class PortalEmailSmokeSettings:
    root: Path
    destination: str
    allowed_destination_hash: str
    discord_username: str
    deployment_id: str
    credential_path: Path

    def validate(self) -> None:
        if not secrets_compare(
            destination_fingerprint(self.destination), self.allowed_destination_hash
        ):
            raise PortalEmailSmokeError("DESTINATION_ALLOWLIST_MISMATCH")
        if not SAFE_USERNAME.fullmatch(self.discord_username):
            raise PortalEmailSmokeError("DISCORD_USERNAME_INVALID")
        if self.root.exists() and self.root.is_symlink():
            raise PortalEmailSmokeError("TEMP_ROOT_SYMLINK_REFUSED")
        if not self.credential_path.is_file() or self.credential_path.is_symlink():
            raise PortalEmailSmokeError("OAUTH_CREDENTIAL_INVALID")
        if stat.S_IMODE(self.credential_path.stat().st_mode) & 0o077:
            raise PortalEmailSmokeError("OAUTH_CREDENTIAL_MODE_INVALID")
        if not self.deployment_id.strip():
            raise PortalEmailSmokeError("GAS_DEPLOYMENT_ID_MISSING")


def _request(
    *,
    path: str,
    payload: Mapping[str, str],
    cookie: str | None = None,
    csrf: str | None = None,
) -> PortalRequest:
    headers = {
        "Host": HOST,
        "Origin": ORIGIN,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    if cookie is not None:
        headers["Cookie"] = cookie
    if csrf is not None:
        headers["X-CSRF-Token"] = csrf
    return PortalRequest(
        method="POST",
        target=path,
        headers=headers,
        body=urlencode(payload).encode("utf-8"),
        client_key="controlled-email-smoke",
    )


def _join_session(backend: PortalBackend) -> tuple[str, str]:
    response = backend.handle(_request(path=SESSION_PATH, payload={"scope": "JOIN"}))
    if response.status != 201:
        raise PortalEmailSmokeError("SESSION_ISSUE_FAILED")
    raw_cookies = response.headers.get("Set-Cookie")
    if not isinstance(raw_cookies, tuple) or len(raw_cookies) != 2:
        raise PortalEmailSmokeError("SESSION_COOKIE_INVALID")
    cookie_pairs = [value.split(";", 1)[0] for value in raw_cookies]
    csrf_pair = next(
        (value for value in cookie_pairs if value.startswith(f"{JOIN_CSRF_COOKIE}=")), None
    )
    if csrf_pair is None:
        raise PortalEmailSmokeError("CSRF_COOKIE_MISSING")
    return "; ".join(cookie_pairs), csrf_pair.split("=", 1)[1]


def run_email_smoke(
    settings: PortalEmailSmokeSettings,
    transport: AppsScriptApiTransport,
    *,
    code_reader: Callable[[], str],
    progress: Callable[[str], None] = lambda _event: None,
) -> dict[str, str]:
    settings.validate()
    settings.root.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.chmod(settings.root, 0o700)
    database = settings.root / "portal-email-smoke.sqlite3"
    audit_database = settings.root / "portal-email-smoke-audit.sqlite3"
    store = AllowlistedPortalStore(database, settings.allowed_destination_hash)
    audit = SQLiteAuditSink(audit_database)
    try:
        store.repository.set_config("portal.synthetic_only", 1)
        store.repository.set_config("portal.environment", "STAGING")
        store.repository.set_config("live_discord_enabled", 0)
        store.repository.set_config("portal.email_transport", "REAL_GAS_CONTROLLED_SMOKE")
        backend = PortalBackend(
            store,
            settings=PortalBackendSettings(origin=ORIGIN, secure_cookies=False),
            sessions=SignedSessionAuthorizer(os.urandom(32), key_id="email-smoke-v1"),
            audit=audit,
        )
        cookie, csrf = _join_session(backend)
        started = backend.handle(
            _request(
                path=EMAIL_START_PATH,
                payload={"identityType": "GUEST", "email": settings.destination},
                cookie=cookie,
                csrf=csrf,
            )
        )
        if started.status != 202:
            raise PortalEmailSmokeError("EMAIL_CHALLENGE_START_FAILED")
        challenge_id = str(started.json().get("challengeId", ""))
        if not challenge_id:
            raise PortalEmailSmokeError("EMAIL_CHALLENGE_ID_MISSING")

        delivery = deliver_verification_email_once(
            BridgeSettings(
                database_path=database,
                deployment_id=settings.deployment_id,
                credential_path=settings.credential_path,
                sheet_fingerprint="controlled-email-smoke",
                environment="STAGING",
                synthetic_only=True,
                interval_seconds=60,
                staging_lab_root=settings.root,
            ),
            transport,
        )
        if delivery.get("status") != "COMPLETED":
            raise PortalEmailSmokeError(str(delivery.get("safeResultCode", "EMAIL_SEND_FAILED")))
        progress("EMAIL_SENT_WAITING_FOR_CODE")

        code = code_reader().strip()
        if not re.fullmatch(r"[0-9]{6}", code):
            raise PortalEmailSmokeError("VERIFICATION_CODE_FORMAT_INVALID")
        verified = backend.handle(
            _request(
                path=EMAIL_VERIFY_PATH,
                payload={"challengeId": challenge_id, "code": code},
                cookie=cookie,
                csrf=csrf,
            )
        )
        if verified.status != 200:
            raise PortalEmailSmokeError("EMAIL_VERIFICATION_REJECTED")

        submitted = backend.handle(
            _request(
                path=JOIN_PATH,
                payload={
                    "identityType": "GUEST",
                    "discordUsername": settings.discord_username,
                    "guestEmail": settings.destination,
                    "guestReason": "受控 Portal Email 全鏈路驗收，不連 Discord production。",
                    "rulesPrivacy": "yes",
                    "emailVerificationId": challenge_id,
                },
                cookie=cookie,
                csrf=csrf,
            )
        )
        if submitted.status != 202 or submitted.json().get("outcome") != "ACCEPTED":
            raise PortalEmailSmokeError("JOIN_SUBMISSION_FAILED")

        application = store.repository._connection.execute(  # noqa: SLF001
            "SELECT status FROM join_applications"
        ).fetchall()
        outbox = store.repository._connection.execute(  # noqa: SLF001
            "SELECT status, destination, verification_code FROM email_delivery_outbox"
        ).fetchone()
        challenge = store.repository._connection.execute(  # noqa: SLF001
            "SELECT status FROM email_verification_challenges WHERE challenge_id = ?",
            (challenge_id,),
        ).fetchone()
        if len(application) != 1 or application[0]["status"] != "PENDING_REVIEW":
            raise PortalEmailSmokeError("JOIN_APPLICATION_STATE_INVALID")
        if outbox is None or tuple(outbox) != ("COMPLETED", None, None):
            raise PortalEmailSmokeError("EMAIL_OUTBOX_NOT_SCRUBBED")
        if challenge is None or challenge["status"] != "CONSUMED":
            raise PortalEmailSmokeError("EMAIL_CHALLENGE_NOT_CONSUMED")
        audit_rows = audit._connection.execute(  # noqa: SLF001
            "SELECT event_type, route, outcome, actor_fingerprint, occurred_at "
            "FROM portal_audit_events"
        ).fetchall()
        serialized_audit = json.dumps([tuple(row) for row in audit_rows], default=str)
        if settings.destination in serialized_audit or code in serialized_audit:
            raise PortalEmailSmokeError("AUDIT_REDACTION_FAILED")
        return {
            "portalEmailSmoke": "PASS",
            "emailDelivery": "COMPLETED",
            "emailChallenge": "CONSUMED",
            "joinApplication": "PENDING_REVIEW",
            "productionDatabaseModified": "NO",
            "discordMutation": "NO",
            "sensitiveValuesPrinted": "NO",
        }
    finally:
        store.close()
        audit.close()


def _required_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise PortalEmailSmokeError(f"{name}_MISSING")
    return value


def main() -> None:
    if os.environ.get("PORTAL_EMAIL_SMOKE") != "1":
        raise SystemExit("portal_email_smoke=REFUSED_EXPLICIT_ENABLE_REQUIRED")
    destination = _required_environment("PORTAL_EMAIL_SMOKE_DESTINATION")
    allowed_hash = _required_environment("PORTAL_EMAIL_SMOKE_DESTINATION_SHA256")
    try:
        with tempfile.TemporaryDirectory(prefix="calculus-portal-email-smoke.") as temporary:
            settings = PortalEmailSmokeSettings(
                root=Path(temporary) / "isolated",
                destination=destination,
                allowed_destination_hash=allowed_hash,
                discord_username=_required_environment("PORTAL_EMAIL_SMOKE_DISCORD_USERNAME"),
                deployment_id=_required_environment("GAS_DEPLOYMENT_ID"),
                credential_path=Path(_required_environment("GOOGLE_OAUTH_CREDENTIALS")),
            )
            result = run_email_smoke(
                settings,
                AppsScriptApiTransport(
                    AppsScriptApiConfig(settings.deployment_id, settings.credential_path)
                ),
                code_reader=lambda: getpass.getpass("verification_code="),
                progress=lambda event: print(f"portal_email_smoke={event}", flush=True),
            )
            for key, value in result.items():
                print(f"{key}={value}")
    except PortalEmailSmokeError as error:
        raise SystemExit(f"portal_email_smoke=FAIL_{error}") from None


if __name__ == "__main__":
    main()
