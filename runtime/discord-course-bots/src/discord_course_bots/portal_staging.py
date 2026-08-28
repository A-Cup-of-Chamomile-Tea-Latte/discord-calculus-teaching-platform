from __future__ import annotations

import argparse
import json
import mimetypes
import os
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from .apps_script_transport import AppsScriptApiError
from .portal_backend import (
    PortalBackend,
    PortalBackendSettings,
    PortalEmailDestinationRefused,
    PortalHTTPServer,
    PortalRequestHandler,
    SignedSessionAuthorizer,
    SQLiteAuditSink,
    SqlitePortalStore,
)
from .production_bridge import BridgeSettings, deliver_verification_email_once

MARKER_NAME = ".portal-synthetic-staging.json"
DATABASE_NAME = "portal.synthetic.sqlite3"
AUDIT_DATABASE_NAME = "portal-audit.synthetic.sqlite3"
EMAIL_CAPTURE_NAME = "captured-email.synthetic.jsonl"
FIXTURE_DESTINATIONS = frozenset({"synthetic.student@ntu.edu.tw", "synthetic.guest@example.com"})


class SyntheticStagingError(RuntimeError):
    """The requested directory is not an isolated synthetic Portal staging root."""


def resolve_static_path(root: Path, target: str) -> Path | None:
    """Resolve one static Portal path without directory listing or traversal."""
    parsed = urlsplit(target)
    if parsed.query or parsed.fragment:
        return None
    try:
        relative = Path(unquote(parsed.path).lstrip("/"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not relative.parts:
        relative = Path("index.html")
    elif parsed.path.endswith("/"):
        relative /= "index.html"
    try:
        current = root
        for part in relative.parts:
            current /= part
            if current.is_symlink():
                return None
        candidate = current.resolve(strict=True)
        candidate.relative_to(root.resolve(strict=True))
    except (OSError, RuntimeError, ValueError):
        return None
    if not candidate.is_file():
        return None
    return candidate


class SyntheticPortalRequestHandler(PortalRequestHandler):
    """Serve the connected static artifact and API from one loopback origin."""

    server: SyntheticPortalHTTPServer

    def do_HEAD(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._dispatch_static()

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self._is_api_request():
            self._dispatch_api()
            return
        self._dispatch_static()

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self._is_api_request():
            self._dispatch_api()
            return
        self.send_error(404)

    def _is_api_request(self) -> bool:
        path = urlsplit(self.path).path
        base = self.server.static_base_path
        return path.startswith("/api/") if base == "/" else path.startswith(f"{base}/api/")

    def _dispatch_api(self) -> None:
        original = self.path
        base = self.server.static_base_path
        if base != "/":
            self.path = self.path[len(base) :]
        try:
            super()._dispatch()
        finally:
            self.path = original

    def _dispatch_static(self) -> None:
        target_path = urlsplit(self.path).path
        base = self.server.static_base_path
        if base != "/":
            if target_path == base:
                target_path = f"{base}/"
            if not target_path.startswith(f"{base}/"):
                self.send_error(404)
                return
            target_path = target_path[len(base) :]
        path = resolve_static_path(self.server.static_root, target_path)
        if path is None:
            self.send_error(404)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
        )
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)


class SyntheticPortalHTTPServer(PortalHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        backend: PortalBackend,
        static_root: Path,
        static_base_path: str = "/",
    ) -> None:
        resolved = static_root.resolve()
        if static_root.is_symlink() or not resolved.is_dir():
            raise SyntheticStagingError("STATIC_ROOT_INVALID")
        self.backend = backend
        self.static_root = resolved
        self.static_base_path = static_base_path
        ThreadingHTTPServer.__init__(self, address, SyntheticPortalRequestHandler)


class CapturingEmailTransport:
    """Capture fixture verification mail locally without any network provider."""

    transport_name = "synthetic-file-capture"

    def __init__(self, path: Path) -> None:
        self.path = path

    def send_verification_email(self, delivery: dict[str, object]) -> dict[str, object]:
        destination = str(delivery.get("destination", "")).casefold()
        if destination not in FIXTURE_DESTINATIONS:
            raise AppsScriptApiError("STAGING_DESTINATION_REFUSED")
        record = {
            "deliveryId": str(delivery["deliveryId"]),
            "destination": destination,
            "code": str(delivery["code"]),
            "kind": str(delivery["kind"]),
            "expiresAt": str(delivery["expiresAt"]),
            "syntheticOnly": True,
        }
        descriptor = os.open(
            self.path,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o600,
        )
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        return {
            "deliveryId": delivery["deliveryId"],
            "status": "PROVIDER_ACCEPTED",
            "safeResultCode": "EMAIL_PROVIDER_ACCEPTED",
            "quotaRemainingBefore": 1_000,
        }


class SyntheticPortalStore(SqlitePortalStore):
    """Canonical adapter with a staging-only guard against real Email input."""

    @staticmethod
    def _require_fixture_destination(destination: object) -> None:
        if str(destination).strip().casefold() not in FIXTURE_DESTINATIONS:
            raise PortalEmailDestinationRefused("STAGING_DESTINATION_REFUSED")

    def start_email_verification(self, **kwargs: Any) -> str:
        self._require_fixture_destination(kwargs.get("destination"))
        return super().start_email_verification(**kwargs)

    def submit_join_application(self, **kwargs: Any) -> tuple[Mapping[str, Any], bool]:
        self._require_fixture_destination(kwargs.get("identity_email"))
        return super().submit_join_application(**kwargs)


@dataclass(slots=True)
class SyntheticPortalStaging:
    root: Path
    database_path: Path
    audit_database_path: Path
    email_capture_path: Path
    general_case_number: str
    private_case_number: str
    store: SyntheticPortalStore
    audit: SQLiteAuditSink
    backend: PortalBackend

    def close(self) -> None:
        self.store.close()
        self.audit.close()


def _prepare_root(root: Path) -> Path:
    expanded = root.expanduser()
    if expanded.exists() and expanded.is_symlink():
        raise SyntheticStagingError("STAGING_ROOT_SYMLINK_REFUSED")
    resolved = expanded.resolve()
    if resolved in {Path("/"), Path.home().resolve()} or len(resolved.parts) < 3:
        raise SyntheticStagingError("STAGING_ROOT_TOO_BROAD")
    resolved.mkdir(mode=0o700, parents=True, exist_ok=True)
    marker = resolved / MARKER_NAME
    entries = list(resolved.iterdir())
    if entries and not marker.is_file():
        raise SyntheticStagingError("UNMARKED_NONEMPTY_STAGING_ROOT")
    expected = {"schemaVersion": "1.0", "environment": "STAGING", "syntheticOnly": True}
    if marker.exists():
        try:
            if json.loads(marker.read_text(encoding="utf-8")) != expected:
                raise SyntheticStagingError("STAGING_MARKER_INVALID")
        except json.JSONDecodeError as exc:
            raise SyntheticStagingError("STAGING_MARKER_INVALID") from exc
    else:
        descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(expected, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
    os.chmod(resolved, 0o700)
    return resolved


def _seed_case(
    store: SqlitePortalStore,
    *,
    case_id: str,
    thread_id: int,
    private: bool,
) -> str:
    existing = store.repository._connection.execute(  # noqa: SLF001
        "SELECT case_number FROM cases WHERE case_id = ?", (case_id,)
    ).fetchone()
    if existing is not None:
        return str(existing["case_number"])
    case_number = store.repository.create_case(
        case_id=case_id,
        thread_id=thread_id,
        author_id=90_000 + thread_id,
        ai_content_permission=False,
        module_code="M1",
        keyword="隱密支援" if private else "極限",
        canonical_title="[Synthetic] Portal staging fixture",
        initial_snapshot={"body": "synthetic staging content must never enter Portal lookup"},
        class_code=None if private else "01",
        private_support=private,
    )
    store.repository.set_case_jump_url(
        thread_id,
        f"https://discord.example.invalid/channels/synthetic/{thread_id}",
    )
    return case_number


def create_synthetic_staging(
    root: Path,
    *,
    origin: str,
    session_secret: bytes,
    secure_cookies: bool = True,
    trusted_proxy_ips: frozenset[str] = frozenset(),
) -> SyntheticPortalStaging:
    parsed_origin = urlsplit(origin)
    if secure_cookies and (
        parsed_origin.scheme != "https"
        or not parsed_origin.netloc
        or parsed_origin.path not in {"", "/"}
        or parsed_origin.query
        or parsed_origin.fragment
    ):
        raise SyntheticStagingError("HTTPS_ORIGIN_REQUIRED")
    if len(session_secret) < 32:
        raise SyntheticStagingError("STAGING_SESSION_SECRET_TOO_SHORT")
    parsed_root = _prepare_root(root)
    database = parsed_root / DATABASE_NAME
    audit_database = parsed_root / AUDIT_DATABASE_NAME
    email_capture = parsed_root / EMAIL_CAPTURE_NAME
    store = SyntheticPortalStore(database)
    audit: SQLiteAuditSink | None = None
    try:
        existing_mode = store.repository.get_config("portal.synthetic_only")
        existing_environment = store.repository.get_config("portal.environment")
        if existing_mode not in {None, "1"} or existing_environment not in {None, "STAGING"}:
            raise SyntheticStagingError("NON_SYNTHETIC_DATABASE_REFUSED")
        store.repository.set_config("portal.synthetic_only", 1)
        store.repository.set_config("portal.environment", "STAGING")
        store.repository.set_config("live_discord_enabled", 0)
        store.repository.set_config("portal.email_transport", "CAPTURE_ONLY")
        general = _seed_case(
            store,
            case_id="synthetic-portal-general",
            thread_id=91_001,
            private=False,
        )
        private = _seed_case(
            store,
            case_id="synthetic-portal-private",
            thread_id=91_002,
            private=True,
        )
        audit = SQLiteAuditSink(audit_database)
        settings = PortalBackendSettings(
            origin=origin,
            secure_cookies=secure_cookies,
            trusted_proxy_ips=trusted_proxy_ips,
        )
        sessions = SignedSessionAuthorizer(
            session_secret,
            key_id="staging-v1",
            max_age_seconds=settings.session_ttl_seconds,
        )
        backend = PortalBackend(store, settings=settings, sessions=sessions, audit=audit)
        return SyntheticPortalStaging(
            root=parsed_root,
            database_path=database,
            audit_database_path=audit_database,
            email_capture_path=email_capture,
            general_case_number=general,
            private_case_number=private,
            store=store,
            audit=audit,
            backend=backend,
        )
    except Exception:
        store.close()
        if audit is not None:
            audit.close()
        raise


def deliver_captured_email_once(staging: SyntheticPortalStaging) -> dict[str, Any]:
    settings = BridgeSettings(
        database_path=staging.database_path,
        deployment_id="synthetic-capture",
        credential_path=staging.root / "no-google-credential",
        sheet_fingerprint="synthetic-capture",
        environment="STAGING",
        synthetic_only=True,
        interval_seconds=60,
        staging_lab_root=staging.root,
    )
    return deliver_verification_email_once(
        settings,
        CapturingEmailTransport(staging.email_capture_path),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run isolated synthetic Portal staging")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--bind-host", default="127.0.0.1")
    parser.add_argument("--bind-port", default=8081, type=int)
    parser.add_argument("--static-root", type=Path)
    parser.add_argument("--base-path", default="/")
    parser.add_argument("--trusted-proxy", action="append", default=[])
    parser.add_argument("--require-production-paths-inaccessible", action="store_true")
    parser.add_argument("--allow-loopback-http", action="store_true")
    args = parser.parse_args()
    if os.environ.get("PORTAL_STAGING_SYNTHETIC_ONLY") != "1":
        raise SystemExit("PORTAL_STAGING_SYNTHETIC_ONLY=1 is required")
    secret = os.environ.get("PORTAL_STAGING_SESSION_SECRET", "").encode()
    if args.base_path != "/" and (
        not args.base_path.startswith("/") or args.base_path.endswith("/") or "//" in args.base_path
    ):
        raise SystemExit(
            "base path must be / or a normalized absolute path without a trailing slash"
        )
    trusted_proxies = frozenset(args.trusted_proxy)
    if args.require_production_paths_inaccessible:
        for protected in (Path("/var/lib/calculus-discord"), Path("/etc/calculus-discord")):
            try:
                protected.stat()
            except PermissionError:
                continue
            except FileNotFoundError:
                raise SystemExit(f"required production boundary is absent: {protected}") from None
            raise SystemExit(f"production path is accessible: {protected}")
    if args.allow_loopback_http:
        expected_origins = {
            f"http://127.0.0.1:{args.bind_port}",
            f"http://localhost:{args.bind_port}",
        }
        if args.bind_host not in {"127.0.0.1", "::1"} or args.origin not in expected_origins:
            raise SystemExit("loopback HTTP requires an exact localhost origin and bind address")
    staging = create_synthetic_staging(
        args.root,
        origin=args.origin,
        session_secret=secret,
        secure_cookies=not args.allow_loopback_http,
        trusted_proxy_ips=trusted_proxies,
    )
    stop = threading.Event()
    worker_failure: list[str] = []

    if args.static_root is None:
        server = PortalHTTPServer((args.bind_host, args.bind_port), staging.backend)
    else:
        server = SyntheticPortalHTTPServer(
            (args.bind_host, args.bind_port),
            staging.backend,
            args.static_root,
            args.base_path,
        )

    def capture_worker() -> None:
        while not stop.wait(0.5):
            try:
                deliver_captured_email_once(staging)
            except Exception:
                worker_failure.append("EMAIL_CAPTURE_WORKER_FAILED")
                stop.set()
                server.shutdown()
                return

    worker = threading.Thread(target=capture_worker, name="portal-email-capture", daemon=True)
    worker.start()
    print(
        json.dumps(
            {
                "portalStaging": "READY",
                "syntheticOnly": True,
                "database": str(staging.database_path),
                "auditDatabase": str(staging.audit_database_path),
                "emailCapture": str(staging.email_capture_path),
                "generalCase": staging.general_case_number,
                "privateCase": staging.private_case_number,
                "productionConnected": False,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        worker.join(timeout=2)
        server.server_close()
        staging.close()
    if worker_failure:
        raise SystemExit(f"portal_staging={worker_failure[0]}")


if __name__ == "__main__":
    main()
