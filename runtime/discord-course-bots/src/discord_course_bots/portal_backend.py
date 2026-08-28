"""Authenticated same-origin Portal endpoints.

This module is deliberately a small boundary around the canonical v13 SQLite
repository.  The browser never receives a repository row, Discord credential,
or internal identifier.  The HTTP layer only accepts one join submission or
one case-number lookup per request.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
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
EMAIL_START_PATH = "/api/join/email/start"
EMAIL_VERIFY_PATH = "/api/join/email/verify"
CASE_LOOKUP_PATH = "/api/cases/lookup"
SESSION_PATH = "/api/session"
HEALTH_PATH = "/api/health"
PORTAL_ROUTES = frozenset(
    {HEALTH_PATH, SESSION_PATH, JOIN_PATH, EMAIL_START_PATH, EMAIL_VERIFY_PATH, CASE_LOOKUP_PATH}
)
CSRF_HEADER = "x-csrf-token"
JOIN_SCOPE = "JOIN"
LOOKUP_SCOPE = "LOOKUP"
SESSION_SCOPES = frozenset({JOIN_SCOPE, LOOKUP_SCOPE})
JOIN_SESSION_COOKIE = "portal_join_session"
LOOKUP_SESSION_COOKIE = "portal_lookup_session"
JOIN_CSRF_COOKIE = "portal_join_csrf"
LOOKUP_CSRF_COOKIE = "portal_lookup_csrf"
CASE_STATUS_VALUES = frozenset({"OPEN", "TRACKED", "IDLE", "CLOSED", "AUTO_CLOSED"})
CASE_NUMBER_RE = re.compile(
    r"^(?:C[0-9]{2}|GUEST)-[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{6}-"
    r"(?:0[1-9]|1[0-2])(?:0[1-9]|[12][0-9]|3[01])-"
    r"(?:[01][0-9]|2[0-3])[0-5][0-9](?:-P)?$"
)
SAFE_SESSION_SUBJECT = re.compile(r"^[A-Za-z0-9._:-]{3,128}$")
SAFE_AUDIT_EVENT = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")


class PortalBackendError(RuntimeError):
    """An expected backend failure which must not cross the HTTP boundary."""


class PortalEmailDestinationRefused(PortalBackendError):
    """A deployment policy intentionally refuses this Email destination."""


class ForwardedClientAddressError(ValueError):
    """A trusted proxy supplied no usable single client address."""


def _canonical_ip(value: str) -> str:
    try:
        return str(ipaddress.ip_address(value))
    except ValueError as exc:
        raise ForwardedClientAddressError("CLIENT_ADDRESS_INVALID") from exc


def resolve_client_key(
    peer_ip: str,
    forwarded_values: tuple[str, ...],
    trusted_proxy_ips: frozenset[str],
) -> str:
    """Resolve one rate-limit key without trusting arbitrary forwarding headers."""
    peer = _canonical_ip(peer_ip)
    if peer not in trusted_proxy_ips:
        return peer
    if len(forwarded_values) != 1:
        raise ForwardedClientAddressError("FORWARDED_CLIENT_REQUIRED")
    forwarded = forwarded_values[0]
    if forwarded != forwarded.strip() or "," in forwarded:
        raise ForwardedClientAddressError("FORWARDED_CLIENT_NOT_SINGLE_CANONICAL_IP")
    canonical = _canonical_ip(forwarded)
    if forwarded != canonical:
        raise ForwardedClientAddressError("FORWARDED_CLIENT_NOT_SINGLE_CANONICAL_IP")
    return canonical


class PortalStore(Protocol):
    """The minimum canonical-store surface required by Portal."""

    def submit_join_application(self, **kwargs: Any) -> tuple[Mapping[str, Any], bool]: ...

    def safe_case_projection(
        self, case_number: str, *, allow_private: bool
    ) -> Mapping[str, Any] | None: ...

    def start_email_verification(self, **kwargs: Any) -> str: ...

    def verify_email_challenge(self, **kwargs: Any) -> bool: ...

    def email_verification_matches(self, **kwargs: Any) -> bool: ...

    def consume_email_verification(self, **kwargs: Any) -> bool: ...


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

    def start_email_verification(self, **kwargs: Any) -> str:
        return self.repository.start_email_verification(**kwargs)

    def verify_email_challenge(self, **kwargs: Any) -> bool:
        return self.repository.verify_email_challenge(**kwargs)

    def email_verification_matches(self, **kwargs: Any) -> bool:
        return self.repository.email_verification_matches(**kwargs)

    def consume_email_verification(self, **kwargs: Any) -> bool:
        return self.repository.consume_email_verification(**kwargs)

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
    headers: Mapping[str, str | tuple[str, ...]] = field(default_factory=dict)

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


@dataclass(frozen=True, slots=True)
class PortalBackendSettings:
    origin: str
    join_session_cookie: str = JOIN_SESSION_COOKIE
    lookup_session_cookie: str = LOOKUP_SESSION_COOKIE
    join_csrf_cookie: str = JOIN_CSRF_COOKIE
    lookup_csrf_cookie: str = LOOKUP_CSRF_COOKIE
    session_ttl_seconds: int = 1_800
    max_body_bytes: int = 8_192
    csrf_token_bytes: int = 32
    lookup_min_duration_seconds: float = 0.0
    secure_cookies: bool = True
    trusted_proxy_ips: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        parsed = urlsplit(self.origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("origin must be an absolute http(s) origin")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("origin must not contain a path, query, or fragment")
        if (
            self.max_body_bytes <= 0
            or self.csrf_token_bytes < 16
            or not 60 <= self.session_ttl_seconds <= 3_600
        ):
            raise ValueError("backend limits are unsafe")
        if self.lookup_min_duration_seconds < 0:
            raise ValueError("lookup_min_duration_seconds cannot be negative")
        canonical_proxies = frozenset(_canonical_ip(value) for value in self.trusted_proxy_ips)
        if canonical_proxies != self.trusted_proxy_ips:
            raise ValueError("trusted proxy addresses must be canonical IP literals")


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
        if record.route not in PORTAL_ROUTES:
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
    def issue(self, scope: str) -> str: ...

    def authorize(
        self, request: PortalRequest, *, required_scope: str, cookie_name: str
    ) -> str | None: ...


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    if not value or len(value) > 4_096:
        raise ValueError("invalid base64 value")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class SignedSessionAuthorizer:
    """Issue and verify anonymous, short-lived, scope-bound Portal sessions."""

    def __init__(
        self,
        secret: bytes,
        *,
        key_id: str = "v1",
        previous_keys: Mapping[str, bytes] | None = None,
        max_age_seconds: int = 1_800,
        clock_skew_seconds: int = 60,
        now: callable = time.time,
    ) -> None:
        if len(secret) < 32:
            raise ValueError("session secret must contain at least 32 bytes")
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,32}", key_id):
            raise ValueError("unsafe session key id")
        if max_age_seconds <= 0 or not 0 <= clock_skew_seconds <= 300:
            raise ValueError("unsafe session lifetime policy")
        keys = dict(previous_keys or {})
        keys[key_id] = secret
        if any(
            not re.fullmatch(r"[A-Za-z0-9._-]{1,32}", stored_id) or len(stored_secret) < 32
            for stored_id, stored_secret in keys.items()
        ):
            raise ValueError("unsafe session key ring")
        self.keys = keys
        self.active_key_id = key_id
        self.max_age_seconds = max_age_seconds
        self.clock_skew_seconds = clock_skew_seconds
        self.now = now

    def issue(self, scope: str) -> str:
        return self._issue(secrets.token_urlsafe(32), (scope,))

    def issue_for_test(
        self,
        subject: str,
        *,
        scopes: tuple[str, ...] = (JOIN_SCOPE, LOOKUP_SCOPE),
        issued_at: int | None = None,
    ) -> str:
        """Create a deterministic-subject token for isolated tests only."""
        return self._issue(subject, scopes, issued_at=issued_at)

    def _issue(self, subject: str, scopes: tuple[str, ...], *, issued_at: int | None = None) -> str:
        if not SAFE_SESSION_SUBJECT.fullmatch(subject):
            raise ValueError("unsafe session subject")
        if not scopes or not set(scopes) <= SESSION_SCOPES:
            raise ValueError("unsafe session scope")
        issued = int(self.now() if issued_at is None else issued_at)
        payload = json.dumps(
            {
                "sub": subject,
                "scp": sorted(set(scopes)),
                "iat": issued,
                "exp": issued + self.max_age_seconds,
                "kid": self.active_key_id,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        encoded = _b64encode(payload)
        signature = hmac.new(
            self.keys[self.active_key_id], encoded.encode("ascii"), hashlib.sha256
        ).digest()
        return f"{encoded}.{_b64encode(signature)}"

    def authorize(
        self, request: PortalRequest, *, required_scope: str, cookie_name: str
    ) -> str | None:
        if required_scope not in SESSION_SCOPES:
            return None
        cookies = _parse_cookies(request.header("cookie"))
        token = cookies.get(cookie_name)
        if token is None:
            return None
        try:
            encoded, supplied_signature = token.split(".", 1)
            payload = json.loads(_b64decode(encoded))
            if set(payload) != {"sub", "scp", "iat", "exp", "kid"}:
                return None
            key_id = payload["kid"]
            secret = self.keys.get(key_id)
            if secret is None:
                return None
            expected_signature = hmac.new(secret, encoded.encode("ascii"), hashlib.sha256).digest()
            if not hmac.compare_digest(_b64decode(supplied_signature), expected_signature):
                return None
            subject = payload["sub"]
            scopes = payload["scp"]
            issued_at = int(payload["iat"])
            expires_at = int(payload["exp"])
            moment = int(self.now())
            if (
                not isinstance(scopes, list)
                or not scopes
                or any(not isinstance(scope, str) for scope in scopes)
                or not set(scopes) <= SESSION_SCOPES
                or required_scope not in scopes
                or not isinstance(subject, str)
                or not SAFE_SESSION_SUBJECT.fullmatch(subject)
                or expires_at - issued_at != self.max_age_seconds
                or moment + self.clock_skew_seconds < issued_at
                or moment - self.clock_skew_seconds > expires_at
            ):
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
    if normalized.startswith("GUEST-") and normalized.endswith("-P"):
        raise ValueError("invalid Guest case number")
    parts = normalized.split("-")
    month = int(parts[2][:2])
    day = int(parts[2][2:])
    maximum_days = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    if day < 1 or day > maximum_days[month - 1]:
        raise ValueError("invalid case date")
    return "Guest-" + normalized[6:] if normalized.startswith("GUEST-") else normalized


def _safe_requested_case_number(value: str) -> str:
    normalized = "".join(value.strip().upper().split())[:32]
    return normalized or "INVALID"


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _response(
    status: int,
    payload: Any,
    *,
    extra_headers: Mapping[str, str | tuple[str, ...]] | None = None,
) -> PortalResponse:
    headers: MutableMapping[str, str | tuple[str, ...]] = {
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
    """Small same-origin Portal backend with fail-closed security middleware."""

    def __init__(
        self,
        store: PortalStore,
        *,
        settings: PortalBackendSettings,
        sessions: SessionAuthorizer,
        audit: PortalAuditSink,
        rate_limiter: RateLimiter | None = None,
        ip_rate_limiter: RateLimiter | None = None,
        global_rate_limiter: RateLimiter | None = None,
        issuer_rate_limiter: RateLimiter | None = None,
        issuer_global_rate_limiter: RateLimiter | None = None,
        clock: callable = _now_iso,
    ) -> None:
        self.store = store
        self.settings = settings
        self.sessions = sessions
        self.audit = audit
        self.rate_limiter = rate_limiter or RateLimiter()
        self.ip_rate_limiter = ip_rate_limiter or RateLimiter(limit=60)
        self.global_rate_limiter = global_rate_limiter or RateLimiter(limit=600)
        self.issuer_rate_limiter = issuer_rate_limiter or RateLimiter(limit=20)
        self.issuer_global_rate_limiter = issuer_global_rate_limiter or RateLimiter(limit=600)
        self.clock = clock

    def handle(self, request: PortalRequest) -> PortalResponse:
        path = urlsplit(request.target).path
        if path not in PORTAL_ROUTES:
            return _error(HTTPStatus.NOT_FOUND, "NOT_FOUND")
        parsed_target = urlsplit(request.target)
        if parsed_target.fragment:
            return _error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
        if not self._same_origin(request, require_origin=request.method.upper() != "GET"):
            return _error(HTTPStatus.FORBIDDEN, "FORBIDDEN")

        method = request.method.upper()
        if path == HEALTH_PATH:
            if method != "GET" or parsed_target.query:
                return _error(HTTPStatus.METHOD_NOT_ALLOWED, "METHOD_NOT_ALLOWED")
            return _response(HTTPStatus.OK, {"status": "ok"})
        if path == SESSION_PATH:
            if method != "POST":
                return _error(HTTPStatus.METHOD_NOT_ALLOWED, "METHOD_NOT_ALLOWED")
            if len(request.body) > self.settings.max_body_bytes:
                return _error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "REQUEST_TOO_LARGE")
            return self._issue_session(request)

        scope = LOOKUP_SCOPE if path == CASE_LOOKUP_PATH else JOIN_SCOPE
        session_cookie, _ = self._cookies_for_scope(scope)
        subject = self.sessions.authorize(
            request,
            required_scope=scope,
            cookie_name=session_cookie,
        )
        if subject is None:
            return _error(HTTPStatus.UNAUTHORIZED, "UNAUTHORIZED")
        actor = _actor_fingerprint(subject)
        if not (
            self.rate_limiter.allow(f"session:{path}:{actor}")
            and self.ip_rate_limiter.allow(f"ip:{path}:{request.client_key}")
            and self.global_rate_limiter.allow(f"global:{path}")
        ):
            return _response(
                HTTPStatus.TOO_MANY_REQUESTS,
                {"error": "RATE_LIMITED", "message": "請稍後再試。"},
                extra_headers={"Retry-After": "60"},
            )

        if method == "GET":
            if parsed_target.query:
                return _error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            return self._csrf_seed(request, scope)
        if method != "POST":
            return _error(HTTPStatus.METHOD_NOT_ALLOWED, "METHOD_NOT_ALLOWED")
        if not self._csrf_valid(request, scope):
            return _error(HTTPStatus.FORBIDDEN, "CSRF_REJECTED")
        if len(request.body) > self.settings.max_body_bytes:
            return _error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "REQUEST_TOO_LARGE")

        if path == JOIN_PATH:
            return self._join(request, subject)
        if path == EMAIL_START_PATH:
            return self._email_start(request, subject)
        if path == EMAIL_VERIFY_PATH:
            return self._email_verify(request, subject)
        return self._lookup(request, subject)

    def _issue_session(self, request: PortalRequest) -> PortalResponse:
        if not (
            self.issuer_rate_limiter.allow(f"issuer-ip:{request.client_key}")
            and self.issuer_global_rate_limiter.allow("issuer-global")
        ):
            return _response(
                HTTPStatus.TOO_MANY_REQUESTS,
                {"error": "RATE_LIMITED", "message": "請稍後再試。"},
                extra_headers={"Retry-After": "60"},
            )
        try:
            payload = self._parse_payload(request)
            if set(payload) != {"scope"}:
                raise PortalBackendError("invalid session fields")
            scope = payload["scope"].strip().upper()
            if scope not in SESSION_SCOPES:
                raise PortalBackendError("invalid session scope")
        except PortalBackendError:
            return _error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
        session_cookie, csrf_cookie = self._cookies_for_scope(scope)
        supplied_token = _parse_cookies(request.header("cookie")).get(session_cookie)
        existing_subject = self.sessions.authorize(
            request,
            required_scope=scope,
            cookie_name=session_cookie,
        )
        token = supplied_token if existing_subject is not None and supplied_token else None
        if token is None:
            token = self.sessions.issue(scope)
        csrf = secrets.token_urlsafe(self.settings.csrf_token_bytes)
        secure = "; Secure" if self.settings.secure_cookies else ""
        max_age = self.settings.session_ttl_seconds
        cookie_headers = (
            f"{session_cookie}={token}; Path=/; Max-Age={max_age}; "
            f"HttpOnly; SameSite=Strict{secure}",
            f"{csrf_cookie}={csrf}; Path=/; Max-Age={max_age}; SameSite=Strict{secure}",
        )
        return _response(
            HTTPStatus.CREATED,
            {
                "schemaVersion": "1.0",
                "outcome": "ISSUED",
                "scope": scope,
                "expiresIn": max_age,
            },
            extra_headers={"Set-Cookie": cookie_headers},
        )

    def _cookies_for_scope(self, scope: str) -> tuple[str, str]:
        if scope == JOIN_SCOPE:
            return self.settings.join_session_cookie, self.settings.join_csrf_cookie
        if scope == LOOKUP_SCOPE:
            return self.settings.lookup_session_cookie, self.settings.lookup_csrf_cookie
        raise PortalBackendError("unknown session scope")

    def _email_start(self, request: PortalRequest, subject: str) -> PortalResponse:
        try:
            payload = self._parse_payload(request)
            if set(payload) != {"identityType", "email"}:
                raise PortalBackendError("invalid verification fields")
            identity = payload["identityType"]
            destination = payload["email"]
            if identity not in {"STUDENT", "GUEST"} or not destination or len(destination) > 254:
                raise PortalBackendError("invalid verification identity")
            kind = "INSTITUTIONAL" if identity == "STUDENT" else "CONTACT"
            challenge_id = self.store.start_email_verification(
                session_subject=subject,
                destination=destination,
                email_kind=kind,
            )
            self._audit("PORTAL_EMAIL_STARTED", EMAIL_START_PATH, "ACCEPTED", subject)
        except PortalEmailDestinationRefused:
            return _error(HTTPStatus.BAD_REQUEST, "EMAIL_DESTINATION_REFUSED")
        except (ValueError, PortalBackendError):
            return _error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
        except Exception:
            LOGGER.error("portal email verification start failure")
            return _error(HTTPStatus.SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE")
        return _response(
            HTTPStatus.ACCEPTED,
            {"schemaVersion": "1.0", "outcome": "ACCEPTED", "challengeId": challenge_id},
        )

    def _email_verify(self, request: PortalRequest, subject: str) -> PortalResponse:
        try:
            payload = self._parse_payload(request)
            if set(payload) != {"challengeId", "code"}:
                raise PortalBackendError("invalid verification fields")
            verified = self.store.verify_email_challenge(
                challenge_id=payload["challengeId"],
                session_subject=subject,
                verification_code=payload["code"],
            )
            outcome = "VERIFIED" if verified else "REJECTED"
            self._audit("PORTAL_EMAIL_VERIFIED", EMAIL_VERIFY_PATH, outcome, subject)
        except PortalBackendError:
            return _error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
        except Exception:
            LOGGER.error("portal email verification check failure")
            return _error(HTTPStatus.SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE")
        if not verified:
            return _error(HTTPStatus.BAD_REQUEST, "VERIFICATION_REJECTED")
        return _response(HTTPStatus.OK, {"schemaVersion": "1.0", "outcome": "VERIFIED"})

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

    def _csrf_seed(self, request: PortalRequest, scope: str) -> PortalResponse:
        _, csrf_cookie = self._cookies_for_scope(scope)
        cookies = _parse_cookies(request.header("cookie"))
        token = cookies.get(csrf_cookie)
        if token is None or not (16 <= len(token) <= 256):
            token = secrets.token_urlsafe(self.settings.csrf_token_bytes)
        cookie = f"{csrf_cookie}={token}; Path=/; SameSite=Strict" + (
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

    def _csrf_valid(self, request: PortalRequest, scope: str) -> bool:
        _, csrf_cookie = self._cookies_for_scope(scope)
        cookie = _parse_cookies(request.header("cookie")).get(csrf_cookie)
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

        challenge_id = str(values.pop("email_verification_id"))
        destination = str(values["identity_email"])
        try:
            if not self.store.email_verification_matches(
                challenge_id=challenge_id,
                session_subject=subject,
                destination=destination,
            ):
                return _error(HTTPStatus.BAD_REQUEST, "EMAIL_NOT_VERIFIED")
            self._audit("PORTAL_JOIN_ATTEMPT", JOIN_PATH, "ATTEMPT", subject)
        except Exception:
            LOGGER.error("portal join audit failure")
            return _error(HTTPStatus.SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE")
        try:
            _, duplicate = self.store.submit_join_application(**values)
            if not self.store.consume_email_verification(
                challenge_id=challenge_id,
                session_subject=subject,
                destination=destination,
            ):
                raise PortalBackendError("verification consumption failed")
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
            "emailVerificationId",
        }
        if set(payload) - allowed or payload.get("rulesPrivacy") != "yes":
            raise PortalBackendError("invalid join fields")
        identity = payload.get("identityType")
        username = payload.get("discordUsername", "")
        if identity not in {"STUDENT", "GUEST"} or not username or len(username) > 32:
            raise PortalBackendError("invalid join identity")
        challenge_id = payload.get("emailVerificationId", "")
        if not re.fullmatch(r"email_verification_[a-f0-9]{32}", challenge_id):
            raise PortalBackendError("invalid email verification")
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
                "email_verification_id": challenge_id,
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
            "email_verification_id": challenge_id,
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
        try:
            client_key = resolve_client_key(
                self.client_address[0],
                tuple(self.headers.get_all("X-Forwarded-For", failobj=[])),
                self.server.backend.settings.trusted_proxy_ips,
            )
        except ForwardedClientAddressError:
            response = _error(HTTPStatus.BAD_REQUEST, "INVALID_FORWARDED_CLIENT")
        else:
            response = None
        if response is None and (
            body_length < 0 or body_length > self.server.backend.settings.max_body_bytes
        ):
            response = _error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "REQUEST_TOO_LARGE")
        elif response is None:
            body = self.rfile.read(body_length) if body_length else b""
            response = self.server.backend.handle(
                PortalRequest(
                    method=self.command,
                    target=self.path,
                    headers={key: value for key, value in self.headers.items()},
                    body=body,
                    client_key=client_key,
                )
            )
        self.send_response(response.status)
        for key, value in response.headers.items():
            values = value if isinstance(value, tuple) else (value,)
            for item in values:
                self.send_header(key, item)
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
