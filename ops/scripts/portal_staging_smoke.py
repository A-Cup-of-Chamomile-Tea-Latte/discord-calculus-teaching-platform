#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.client
import json
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlencode, urlsplit


class SmokeFailure(RuntimeError):
    pass


def normalize_base_path(value: str) -> str:
    if value == "/":
        return ""
    if not value.startswith("/") or value.endswith("/") or "//" in value:
        raise SmokeFailure("BASE_PATH_INVALID")
    return value


class Client:
    def __init__(
        self,
        *,
        target: str,
        origin: str,
        base_path: str,
        forwarded_client: str | None,
    ) -> None:
        parsed_target = urlsplit(target)
        parsed_origin = urlsplit(origin)
        if parsed_target.scheme not in {"http", "https"} or not parsed_target.hostname:
            raise SmokeFailure("TARGET_INVALID")
        if parsed_origin.scheme != "https" or not parsed_origin.netloc:
            raise SmokeFailure("ORIGIN_INVALID")
        self.target = parsed_target
        self.origin = origin
        self.host = parsed_origin.netloc
        self.base_path = normalize_base_path(base_path)
        self.forwarded_client = forwarded_client
        self.cookies: dict[str, str] = {}

    def request(
        self,
        method: str,
        path: str,
        *,
        form: dict[str, str] | None = None,
        csrf: str | None = None,
        use_cookies: bool = True,
    ) -> tuple[int, bytes, http.client.HTTPMessage]:
        connection_type = (
            http.client.HTTPSConnection
            if self.target.scheme == "https"
            else http.client.HTTPConnection
        )
        connection = connection_type(self.target.hostname, self.target.port, timeout=10)
        headers = {"Host": self.host, "Accept": "application/json"}
        if self.forwarded_client:
            headers["X-Forwarded-For"] = self.forwarded_client
        body = None
        if form is not None:
            body = urlencode(form)
            headers["Origin"] = self.origin
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if csrf:
            headers["X-CSRF-Token"] = csrf
        if use_cookies and self.cookies:
            headers["Cookie"] = "; ".join(f"{key}={value}" for key, value in self.cookies.items())
        connection.request(method, f"{self.base_path}{path}", body=body, headers=headers)
        response = connection.getresponse()
        payload = response.read()
        for value in response.headers.get_all("Set-Cookie", []):
            pair = value.split(";", 1)[0]
            key, cookie_value = pair.split("=", 1)
            self.cookies[key] = cookie_value
        status = response.status
        headers_out = response.headers
        connection.close()
        return status, payload, headers_out


def require_status(actual: int, expected: int, label: str) -> None:
    if actual != expected:
        raise SmokeFailure(f"{label}_HTTP_{actual}_EXPECTED_{expected}")


def synthetic_case_numbers(database: Path) -> tuple[str, str]:
    marker = database.parent / ".portal-synthetic-staging.json"
    try:
        marker_payload = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SmokeFailure("SYNTHETIC_MARKER_INVALID") from exc
    if marker_payload.get("syntheticOnly") is not True:
        raise SmokeFailure("SYNTHETIC_MARKER_INVALID")
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        rows = connection.execute(
            "SELECT case_number, private_support FROM cases "
            "WHERE case_id IN ('synthetic-portal-general', 'synthetic-portal-private')"
        ).fetchall()
    by_kind = {bool(private): str(number) for number, private in rows}
    if set(by_kind) != {False, True}:
        raise SmokeFailure("SYNTHETIC_CASES_MISSING")
    return by_kind[False], by_kind[True]


def run_smoke(client: Client, database: Path) -> None:
    status, payload, headers = client.request("GET", "/api/health", use_cookies=False)
    require_status(status, 200, "HEALTH")
    if json.loads(payload) != {"status": "ok"} or headers.get("Cache-Control") != "no-store":
        raise SmokeFailure("HEALTH_RESPONSE_INVALID")

    status, _, _ = client.request("GET", "/", use_cookies=False)
    require_status(status, 200, "STATIC_ROOT")

    status, _, _ = client.request("POST", "/api/session", form={"scope": "LOOKUP"})
    require_status(status, 201, "LOOKUP_SESSION")
    status, _, _ = client.request("GET", "/api/cases/lookup")
    require_status(status, 204, "LOOKUP_CSRF")
    csrf = client.cookies.get("portal_lookup_csrf")
    if not csrf:
        raise SmokeFailure("LOOKUP_CSRF_MISSING")
    general, private = synthetic_case_numbers(database)
    for label, case_number in (("GENERAL", general), ("PRIVATE", private)):
        status, payload, _ = client.request(
            "POST",
            "/api/cases/lookup",
            form={"caseNumber": case_number},
            csrf=csrf,
        )
        require_status(status, 200, f"{label}_LOOKUP")
        projection = json.loads(payload).get("case") or {}
        if any(key in projection for key in ("body", "author_id", "initial_snapshot")):
            raise SmokeFailure(f"{label}_LOOKUP_LEAKED_CONTENT")

    isolated = Client(
        target=client.target.geturl(),
        origin=client.origin,
        base_path=client.base_path or "/",
        forwarded_client=client.forwarded_client,
    )
    status, _, _ = isolated.request("POST", "/api/session", form={"scope": "JOIN"})
    require_status(status, 201, "JOIN_SESSION")
    status, _, _ = isolated.request("GET", "/api/cases/lookup")
    require_status(status, 401, "SCOPE_MISMATCH")
    status, _, _ = isolated.request("GET", "/api/join")
    require_status(status, 204, "JOIN_CSRF")
    join_csrf = isolated.cookies.get("portal_join_csrf")
    status, _, _ = isolated.request(
        "POST",
        "/api/join/email/start",
        form={"identityType": "GUEST", "email": "refused.real@example.net"},
        csrf=join_csrf,
    )
    require_status(status, 400, "REAL_EMAIL_REFUSAL")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke isolated Portal synthetic staging")
    parser.add_argument("--target", required=True)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--base-path", default="/")
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--forwarded-client")
    args = parser.parse_args()
    try:
        run_smoke(
            Client(
                target=args.target,
                origin=args.origin,
                base_path=args.base_path,
                forwarded_client=args.forwarded_client,
            ),
            args.database,
        )
    except (OSError, ValueError, json.JSONDecodeError, SmokeFailure) as exc:
        print(f"portal_staging_smoke=FAIL safe_code={exc}", file=sys.stderr)
        return 1
    print("portal_staging_smoke=PASS")
    print("synthetic_lookup=PASS")
    print("real_email_refused=PASS")
    print("production_database_modified=NO")
    print("discord_mutation=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
