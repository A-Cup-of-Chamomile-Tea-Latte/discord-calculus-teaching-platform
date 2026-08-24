"""Authenticated same-origin Portal endpoints.

This module is deliberately a small boundary around the canonical v10 SQLite
repository.  The browser never receives a repository row, Discord credential,
or internal identifier.  The HTTP layer only accepts one join submission or
one case-number lookup per request.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sqlite3
import threading
import time
import uuid
from collections import deque
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qs, urlsplit

from .repository import Repository

LOGGER = logging.getLogger(__name__)

JOIN_PATH = "/api/join"
CASE_LOOKUP_PATH = "/api/cases/lookup"
CASE_STATUS_PATH = "/api/cases/status"
CSRF_HEADER = "x-csrf-token"
SESSION_COOKIE = "portal_session"
CSRF_COOKIE = "portal_csrf"
CASE_STATUS_VALUES = frozenset({"OPEN", "TRACKED", "IDLE", "CLOSED", "AUTO_CLOSED"})
CASE_NUMBER_RE = re.compile(
    r"^C[0-9]{2}-[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{6}-"
    r"(?:0[1-9]|1[0-2])(?:0[1-9]|[12][0-9]|3[01])-"
    r"(?:[01][0-9]|2[0-3])[0-5][0-9](?:-P)?$"
)
SAFE_SESSION_SUBJECT = re.compile(r"^[A-Za-z0-9._:-]{3,128}$")
SAFE_AUDIT_EVENT = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")


class PortalBackendError(RuntimeError):
    """An expected backend failure which must not cross the HTTP boundary."""


class PortalStore(Protocol):
    """The minimum canonical-store surface required by Portal."""

    def submit_join_application(self, **kwargs: Any) -> tuple[Mapping[str, Any], bool]: ...

    def safe_case_projection(
        self, case_number: str, *, allow_private: bool
    ) -> Mapping[str, Any] | None: ...


class SqlitePortalStore:
    """Adapter over the existing Course Manager / case Repository."""

    def __init__(self, path: Path) -> None:
        self.repository = Repository(path)

    def submit_join_application(self, **kwargs: Any) -> tuple[Mapping[str, Any], bool]:
        return self.repository.submit_join_application(**kwargs)

    def safe_case_projection(
        self, case_number: str, *, allow_private: bool
    ) -> Mapping[str, Any] | None:
        return self.repository.safe_case_projection(case_number, allow_private=allow_private)

    def close(self) -> None:
        self.repository.close()


@dataclass(frozen=True, slots=True)
class PortalRequest:
    method: str
    target: str
    headers: Mapping[str, str]
    body: bytes = b""
    client_key: str = "unknown"

    def header(self, name: str) -> str | None:
        wanted = name.casefold()
        for key, value in self.headers.items():
            if key.casefold() == wanted:
                return value
        return None


@dataclass(frozen=True, slots=True)
class PortalResponse:
    status: int
    body: bytes = b""
    headers: Mapping[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


@dataclass(frozen=True, slots=True)
class PortalBackendSettings:
    origin: str
    session_cookie: str = SESSION_COOKIE
    csrf_cookie: str = CSRF_COOKIE
    max_body_bytes: int = 8_192
    csrf_token_bytes: int = 32
    lookup_min_duration_seconds: float = 0.0
    secure_cookies: bool = True

    def __post_init__(self) -> None:
        parsed = urlsplit(self.origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("origin must be an absolute http(s) origin")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("origin must not contain a path, query, or fragment")
        if self.max_body_bytes <= 0 or self.csrf_token_bytes < 16:
            raise ValueError("backend limits are unsafe")
        if self.lookup_min_duration_seconds < 0:
            raise ValueError("lookup_min_duration_seconds cannot be negative")


@dataclass(frozen=True, slots=True)
class PortalAuditRecord:
    event_type: str
    route: str
    outcome: str
    actor_fingerprint: str
    occurred_at: str


class PortalAuditSink(Protocol):
    def append(self, record: PortalAuditRecord) -> None: ...


class StructuredLogAuditSink:
    """Metadata-only audit sink; never logs request bodies or opaque identifiers."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or LOGGER

    def append(self, record: PortalAuditRecord) -> None:
        if not SAFE_AUDIT_EVENT.fullmatch(record.event_type):
            raise PortalBackendError("unsafe audit event")
        self.logger.info(
            "portal_audit event=%s route=%s outcome=%s actor=%s occurred_at=%s",
            record.event_type,
            record.route,
            record.outcome,
            record.actor_fingerprint,
            record.occurred_at,
        )


class SQLiteAuditSink:
    """Durable metadata-only audit store, separate from operational records."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, timeout=5.0, check_same_thread=False)
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA busy_timeout = 5000")
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS portal_audit_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                route TEXT NOT NULL,
                outcome TEXT NOT NULL,
                actor_fingerprint TEXT NOT NULL,
                occurred_at TEXT NOT NULL
            )
            """
        )
        self._connection.commit()
        self._lock = threading.Lock()

    def append(self, record: PortalAuditRecord) -> None:
        if not SAFE_AUDIT_EVENT.fullmatch(record.event_type):
            raise PortalBackendError("unsafe audit event")
        if record.route not in {JOIN_PATH, CASE_LOOKUP_PATH}:
            raise PortalBackendError("unsafe audit route")
        if not record.actor_fingerprint or len(record.actor_fingerprint) != 16:
            raise PortalBackendError("unsafe audit actor")
        with self._lock:
            try:
                self._connection.execute(
                    """
                    INSERT INTO portal_audit_events(
                        event_id, event_type, route, outcome,
                        actor_fingerprint, occurred_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"portal-audit-{uuid.uuid4().hex}",
                        record.event_type,
                        record.route,
                        record.outcome,
                        record.actor_fingerprint,
                        record.occurred_at,
                    ),
                )
                self._connection.commit()
            except Exception as exc:
                self._connection.rollback()
                raise PortalBackendError("audit storage failure") from exc

    def close(self) -> None:
        with self._lock:
            self._connection.close()


class InMemoryAuditSink:
    """Test-only metadata sink.  It intentionally has no raw request field."""

    def __init__(self) -> None:
        self.records: list[PortalAuditRecord] = []

    def append(self, record: PortalAuditRecord) -> None:
        self.records.append(record)


class SessionAuthorizer(Protocol):
    def authorize(self, request: PortalRequest) -> str | None: ...


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    if not value or len(value) > 4_096:
        raise ValueError("invalid base64 value")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class SignedSessionAuthorizer:
    """Verify a short-lived, HMAC-signed session cookie from the same backend."""

    def __init__(
        self,
        secret: bytes,
        *,
        cookie_name: str = SESSION_COOKIE,
        max_age_seconds: int = 86_400,
        now: callable = time.time,
    ) -> None:
        if len(secret) < 32:
            raise ValueError("session secret must contain at least 32 bytes")
        if max_age_seconds <= 0:
            raise ValueError("session max age must be positive")
        self.secret = secret
        self.cookie_name = cookie_name
        self.max_age_seconds = max_age_seconds
        self.now = now

    def issue_for_test(self, subject: str, *, issued_at: int | None = None) -> str:
        """Create a token for tests and a future trusted session issuer."""
        if not SAFE_SESSION_SUBJECT.fullmatch(subject):
            raise ValueError("unsafe session subject")
        payload = json.dumps(
            {"sub": subject, "iat": int(self.now() if issued_at is None else issued_at)},
            separators=(",", ":"),
        ).encode("utf-8")
        encoded = _b64encode(payload)
        signature = hmac.new(self.secret, encoded.encode("ascii"), hashlib.sha256).digest()
        return f"{encoded}.{_b64encode(signature)}"

    def authorize(self, request: PortalRequest) -> str | None:
        cookies = _parse_cookies(request.header("cookie"))
        token = cookies.get(self.cookie_name)
        if token is None:
            return None
        try:
            encoded, supplied_signature = token.split(".", 1)
            expected_signature = hmac.new(
                self.secret, encoded.encode("ascii"), hashlib.sha256
            ).digest()
            if not hmac.compare_digest(_b64decode(supplied_signature), expected_signature):
                return None
            payload = json.loads(_b64decode(encoded))
            subject = payload["sub"]
            issued_at = int(payload["iat"])
            age = int(self.now()) - issued_at
            if not SAFE_SESSION_SUBJECT.fullmatch(subject) or age < 0 or age > self.max_age_seconds:
                return None
            return subject
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None


class RateLimiter:
    """Bounded fixed-window limiter for each client and route."""

    def __init__(self, *, limit: int = 12, window_seconds: float = 60.0) -> None:
        if limit <= 0 or window_seconds <= 0:
            raise ValueError("rate limit settings must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, *, now: float | None = None) -> bool:
        moment = time.monotonic() if now is None else now
        with self._lock:
            events = self._events.setdefault(key, deque())
            cutoff = moment - self.window_seconds
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(moment)
            if len(self._events) > 10_000:
                self._events = {
                    stored_key: stored_events
                    for stored_key, stored_events in self._events.items()
                    if stored_events and stored_events[-1] > cutoff
                }
            return True


def _parse_cookies(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    result: dict[str, str] = {}
    for part in raw.split(";"):
        name, separator, value = part.strip().partition("=")
        if separator and name and name not in result:
            result[name] = value
    return result


def _actor_fingerprint(subject: str) -> str:
    return hashlib.sha256(subject.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def normalize_case_number(value: str) -> str:
    normalized = "".join(value.strip().upper().split())
    if not CASE_NUMBER_RE.fullmatch(normalized):
        raise ValueError("invalid case number")
    parts = normalized.split("-")
    month = int(parts[2][:2])
    day = int(parts[2][2:])
    maximum_days = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    if day < 1 or day > maximum_days[month - 1]:
        raise ValueError("invalid case date")
    return normalized


def _safe_requested_case_number(value: str) -> str:
    normalized = "".join(value.strip().upper().split())[:32]
    return normalized or "INVALID"


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _response(
    status: int,
    payload: Any,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> PortalResponse:
    headers: MutableMapping[str, str] = {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'none'",
    }
    if extra_headers:
        headers.update(extra_headers)
    body = _json_bytes(payload)
    headers["Content-Length"] = str(len(body))
    return PortalResponse(status=status, body=body, headers=headers)


def _error(status: int, code: str) -> PortalResponse:
    return _response(status, {"error": code, "message": "目前無法完成這項操作。"})


class PortalBackend:
    """Two-route Portal backend with fail-closed security middleware."""

    def __init__(
        self,
        store: PortalStore,
        *,
        settings: PortalBackendSettings,
        sessions: SessionAuthorizer,
        audit: PortalAuditSink,
        rate_limiter: RateLimiter | None = None,
        clock: callable = _now_iso,
    ) -> None:
        self.store = store
        self.settings = settings
        self.sessions = sessions
        self.audit = audit
        self.rate_limiter = rate_limiter or RateLimiter()
        self.clock = clock

    def handle(self, request: PortalRequest) -> PortalResponse:
        path = urlsplit(request.target).path
        if path not in {JOIN_PATH, CASE_LOOKUP_PATH, CASE_STATUS_PATH}:
            return _error(HTTPStatus.NOT_FOUND, "NOT_FOUND")
        parsed_target = urlsplit(request.target)
        if parsed_target.fragment:
            return _error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
        if not self._same_origin(request, require_origin=request.method.upper() != "GET"):
            return _error(HTTPStatus.FORBIDDEN, "FORBIDDEN")

        subject = self.sessions.authorize(request)
        if subject is None:
            return _error(HTTPStatus.UNAUTHORIZED, "UNAUTHORIZED")
        rate_key = f"{request.client_key}:{path}:{_actor_fingerprint(subject)}"
        if not self.rate_limiter.allow(rate_key):
            return _response(
                HTTPStatus.TOO_MANY_REQUESTS,
                {"error": "RATE_LIMITED", "message": "請稍後再試。"},
                extra_headers={"Retry-After": "60"},
            )

        method = request.method.upper()
        if method == "GET":
            if path == CASE_STATUS_PATH:
                query = parse_qs(parsed_target.query, keep_blank_values=True, max_num_fields=2)
                if set(query) != {"caseNumber"} or len(query["caseNumber"]) != 1:
                    return _error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                lookup_request = PortalRequest(
                    method="POST",
                    target=CASE_LOOKUP_PATH,
                    headers={**request.headers, "Content-Type": "application/json"},
                    body=_json_bytes({"caseNumber": query["caseNumber"][0]}),
                    client_key=request.client_key,
                )
                return self._lookup(lookup_request, subject)
            if parsed_target.query:
                return _error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            return self._csrf_seed(request)
        if method != "POST":
            return _error(HTTPStatus.METHOD_NOT_ALLOWED, "METHOD_NOT_ALLOWED")
        if not self._csrf_valid(request):
            return _error(HTTPStatus.FORBIDDEN, "CSRF_REJECTED")
        if len(request.body) > self.settings.max_body_bytes:
            return _error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "REQUEST_TOO_LARGE")

        if path == JOIN_PATH:
            return self._join(request, subject)
        return self._lookup(request, subject)

    def _same_origin(self, request: PortalRequest, *, require_origin: bool) -> bool:
        origin = request.header("origin")
        if require_origin and origin != self.settings.origin:
            return False
        if origin is not None and origin != self.settings.origin:
            return False
        host = request.header("host")
        expected_host = urlsplit(self.settings.origin).netloc
        if host is None or host.casefold() != expected_host.casefold():
            return False
        fetch_site = request.header("sec-fetch-site")
        return fetch_site is None or fetch_site.casefold() == "same-origin"

    def _csrf_seed(self, request: PortalRequest) -> PortalResponse:
        cookies = _parse_cookies(request.header("cookie"))
        token = cookies.get(self.settings.csrf_cookie)
        if token is None or not (16 <= len(token) <= 256):
            token = secrets.token_urlsafe(self.settings.csrf_token_bytes)
        cookie = f"{self.settings.csrf_cookie}={token}; Path=/; SameSite=Strict" + (
            "; Secure" if self.settings.secure_cookies else ""
        )
        return PortalResponse(
            status=HTTPStatus.NO_CONTENT,
            headers={
                "Cache-Control": "no-store",
                "Set-Cookie": cookie,
                "Content-Length": "0",
                "X-Content-Type-Options": "nosniff",
            },
        )

    def _csrf_valid(self, request: PortalRequest) -> bool:
        cookie = _parse_cookies(request.header("cookie")).get(self.settings.csrf_cookie)
        header = request.header(CSRF_HEADER)
        if cookie is None or header is None or len(cookie) > 256 or len(header) > 256:
            return False
        return hmac.compare_digest(cookie, header)

    def _parse_payload(self, request: PortalRequest) -> dict[str, str]:
        content_type = (request.header("content-type") or "").split(";", 1)[0].strip().lower()
        if content_type == "application/json":
            try:
                decoded = json.loads(request.body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise PortalBackendError("invalid json") from exc
            if not isinstance(decoded, dict):
                raise PortalBackendError("payload must be an object")
            if any(
                not isinstance(key, str)
                or (
                    not isinstance(value, str)
                    and not (key == "rulesPrivacy" and isinstance(value, bool))
                )
                for key, value in decoded.items()
            ):
                raise PortalBackendError("payload values must be strings")
            return {
                key: ("yes" if value else "no") if isinstance(value, bool) else value.strip()
                for key, value in decoded.items()
            }
        if content_type == "application/x-www-form-urlencoded":
            try:
                parsed = parse_qs(
                    request.body.decode("utf-8"),
                    keep_blank_values=True,
                    strict_parsing=True,
                    max_num_fields=20,
                )
            except (UnicodeDecodeError, ValueError) as exc:
                raise PortalBackendError("invalid form") from exc
            if any(len(values) != 1 for values in parsed.values()):
                raise PortalBackendError("duplicate form field")
            return {key: values[0].strip() for key, values in parsed.items()}
        raise PortalBackendError("unsupported content type")

    def _join(self, request: PortalRequest, subject: str) -> PortalResponse:
        try:
            payload = self._parse_payload(request)
            values = self._validate_join_payload(payload)
        except PortalBackendError:
            return _error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")

        try:
            self._audit("PORTAL_JOIN_ATTEMPT", JOIN_PATH, "ATTEMPT", subject)
        except Exception:
            LOGGER.error("portal join audit failure")
            return _error(HTTPStatus.SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE")
        try:
            _, duplicate = self.store.submit_join_application(**values)
        except (ValueError, PortalBackendError):
            return _error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
        except Exception:
            LOGGER.error("portal join storage failure")
            self._audit_safely("PORTAL_JOIN_FAILURE", JOIN_PATH, "BACKEND_FAILURE", subject)
            return _error(HTTPStatus.SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE")

        outcome = "DUPLICATE" if duplicate else "ACCEPTED"
        try:
            self.audit.append(
                PortalAuditRecord(
                    event_type="PORTAL_JOIN_STORED",
                    route=JOIN_PATH,
                    outcome=outcome,
                    actor_fingerprint=_actor_fingerprint(subject),
                    occurred_at=self.clock(),
                )
            )
        except Exception:
            LOGGER.error("portal join audit failure")
            return _error(HTTPStatus.SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE")
        return _response(
            HTTPStatus.ACCEPTED,
            {
                "schemaVersion": "1.0",
                "outcome": "ACCEPTED",
                "message": "已收到申請；如需補充資料，Course Manager 會透過 Discord 私訊聯絡。",
            },
        )

    @staticmethod
    def _validate_join_payload(payload: Mapping[str, str]) -> dict[str, Any]:
        allowed = {
            "identityType",
            "discordUsername",
            "ntuEmail",
            "contactGmail",
            "classCode",
            "guestEmail",
            "guestReason",
            "rulesPrivacy",
        }
        if set(payload) - allowed or payload.get("rulesPrivacy") != "yes":
            raise PortalBackendError("invalid join fields")
        identity = payload.get("identityType")
        username = payload.get("discordUsername", "")
        if identity not in {"STUDENT", "GUEST"} or not username or len(username) > 32:
            raise PortalBackendError("invalid join identity")
        if identity == "STUDENT":
            if payload.get("guestEmail") or payload.get("guestReason"):
                raise PortalBackendError("cross-identity fields")
            ntu_email = payload.get("ntuEmail", "")
            class_code = payload.get("classCode", "")
            contact_gmail = payload.get("contactGmail", "")
            if not ntu_email or not class_code or len(ntu_email) > 254 or len(contact_gmail) > 254:
                raise PortalBackendError("invalid student fields")
            return {
                "applicant_type": "STUDENT",
                "discord_username": username,
                "identity_email": ntu_email,
                "ntu_mail": ntu_email,
                "contact_email": contact_gmail or None,
                "class_code": class_code,
            }
        guest_email = payload.get("guestEmail", "")
        guest_reason = payload.get("guestReason", "")
        if payload.get("ntuEmail") or payload.get("contactGmail") or payload.get("classCode"):
            raise PortalBackendError("cross-identity fields")
        if not guest_email or not 10 <= len(guest_reason) <= 500 or len(guest_email) > 254:
            raise PortalBackendError("invalid guest fields")
        return {
            "applicant_type": "VISITOR",
            "discord_username": username,
            "identity_email": guest_email,
            "contact_email": guest_email,
            "visit_reason": guest_reason,
        }

    def _lookup(self, request: PortalRequest, subject: str) -> PortalResponse:
        started = time.monotonic()
        try:
            try:
                payload = self._parse_payload(request)
            except PortalBackendError:
                return _error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            if set(payload) != {"caseNumber"}:
                return _error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            raw_case_number = payload["caseNumber"]
            requested = _safe_requested_case_number(raw_case_number)
            try:
                normalized = normalize_case_number(raw_case_number)
            except ValueError:
                result = self._lookup_response(requested, "INVALID", None)
                self._audit("PORTAL_CASE_LOOKUP", CASE_LOOKUP_PATH, "INVALID", subject)
                return result

            projection = self.store.safe_case_projection(normalized, allow_private=True)
            case = self._allowlisted_case_projection(projection) if projection else None
            outcome = "FOUND" if case is not None else "NOT_FOUND"
            self._audit("PORTAL_CASE_LOOKUP", CASE_LOOKUP_PATH, outcome, subject)
            return self._lookup_response(normalized, outcome, case)
        except Exception:
            LOGGER.error("portal case lookup failure")
            self._audit_safely(
                "PORTAL_CASE_LOOKUP_FAILURE", CASE_LOOKUP_PATH, "BACKEND_FAILURE", subject
            )
            return _error(HTTPStatus.SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE")
        finally:
            remaining = self.settings.lookup_min_duration_seconds - (time.monotonic() - started)
            if remaining > 0:
                time.sleep(remaining)

    def _allowlisted_case_projection(
        self, projection: Mapping[str, Any] | None
    ) -> dict[str, Any] | None:
        if projection is None:
            return None
        required = {
            "caseNumber",
            "caseType",
            "status",
            "updatedAt",
            "teachingTeamReplied",
            "discordUrl",
        }
        if set(projection) != required:
            raise PortalBackendError("unsafe case projection")
        case_number = projection["caseNumber"]
        case_type = projection["caseType"]
        status = projection["status"]
        updated_at = projection["updatedAt"]
        replied = projection["teachingTeamReplied"]
        discord_url = projection["discordUrl"]
        if (
            not isinstance(case_number, str)
            or not isinstance(case_type, str)
            or case_type not in {"GENERAL", "PRIVATE_SUPPORT"}
            or not isinstance(status, str)
            or status not in CASE_STATUS_VALUES
            or not isinstance(updated_at, str)
            or not isinstance(replied, bool)
        ):
            raise PortalBackendError("unsafe case projection")
        if discord_url == "":
            discord_url = None
        if discord_url is not None:
            if not isinstance(discord_url, str):
                raise PortalBackendError("unsafe discord url")
            parsed_url = urlsplit(discord_url)
            if parsed_url.scheme != "https" or not parsed_url.netloc:
                raise PortalBackendError("unsafe discord url")
        return {
            "caseNumber": case_number,
            "caseType": case_type,
            "status": status,
            "updatedAt": updated_at,
            "teachingTeamReplied": replied,
            "discordUrl": discord_url,
        }

    def _lookup_response(
        self, requested: str, outcome: str, case: Mapping[str, Any] | None
    ) -> PortalResponse:
        return _response(
            HTTPStatus.OK,
            {
                "schemaVersion": "1.0",
                "requestedCaseNumber": requested,
                "outcome": outcome,
                "case": dict(case) if case is not None else None,
                "lookedUpAt": self.clock(),
            },
        )

    def _audit(self, event_type: str, route: str, outcome: str, subject: str) -> None:
        self.audit.append(
            PortalAuditRecord(
                event_type=event_type,
                route=route,
                outcome=outcome,
                actor_fingerprint=_actor_fingerprint(subject),
                occurred_at=self.clock(),
            )
        )

    def _audit_safely(self, event_type: str, route: str, outcome: str, subject: str) -> None:
        try:
            self._audit(event_type, route, outcome, subject)
        except Exception:
            LOGGER.error("portal audit sink failure")


class PortalRequestHandler(BaseHTTPRequestHandler):
    """stdlib HTTP adapter; deployment owns TLS and the reverse-proxy origin."""

    server: PortalHTTPServer

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._dispatch()

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._dispatch()

    def _dispatch(self) -> None:
        length = self.headers.get("Content-Length", "0")
        try:
            body_length = int(length)
        except ValueError:
            body_length = self.server.backend.settings.max_body_bytes + 1
        if body_length < 0 or body_length > self.server.backend.settings.max_body_bytes:
            response = _error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "REQUEST_TOO_LARGE")
        else:
            body = self.rfile.read(body_length) if body_length else b""
            response = self.server.backend.handle(
                PortalRequest(
                    method=self.command,
                    target=self.path,
                    headers={key: value for key, value in self.headers.items()},
                    body=body,
                    client_key=self.client_address[0],
                )
            )
        self.send_response(response.status)
        for key, value in response.headers.items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(response.body)

    def log_message(self, _format: str, *_args: Any) -> None:
        return


class PortalHTTPServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], backend: PortalBackend) -> None:
        self.backend = backend
        super().__init__(address, PortalRequestHandler)


def main() -> None:
    """Local/runtime entrypoint; production rollout remains an external gate."""
    origin = os.environ.get("PORTAL_ORIGIN")
    secret = os.environ.get("PORTAL_SESSION_SECRET")
    database = os.environ.get("PORTAL_SQLITE_PATH")
    audit_database = os.environ.get("PORTAL_AUDIT_SQLITE_PATH")
    if not origin or not secret or not database or not audit_database:
        raise SystemExit(
            "PORTAL_ORIGIN, PORTAL_SESSION_SECRET, PORTAL_SQLITE_PATH and "
            "PORTAL_AUDIT_SQLITE_PATH are required"
        )
    store = SqlitePortalStore(Path(database))
    sessions = SignedSessionAuthorizer(secret.encode("utf-8"))
    audit = SQLiteAuditSink(Path(audit_database))
    backend = PortalBackend(
        store,
        settings=PortalBackendSettings(origin=origin),
        sessions=sessions,
        audit=audit,
    )
    host = os.environ.get("PORTAL_BIND_HOST", "127.0.0.1")
    port = int(os.environ.get("PORTAL_BIND_PORT", "8080"))
    server = PortalHTTPServer((host, port), backend)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        store.close()
        audit.close()


if __name__ == "__main__":
    main()
