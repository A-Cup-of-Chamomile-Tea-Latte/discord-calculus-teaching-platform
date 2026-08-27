from __future__ import annotations

import json
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from discord_course_bots.apps_script_transport import (
    APPS_SCRIPT_SCOPES,
    AppsScriptApiConfig,
    AppsScriptApiError,
    AppsScriptApiTransport,
)


def credentials(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "token": "fixture-access-token",
                "refresh_token": "fixture-refresh-token",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "fixture-client",
                "client_secret": "fixture-secret",
                "scopes": list(APPS_SCRIPT_SCOPES),
                "expiry": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            }
        ),
        encoding="utf-8",
    )


def test_transport_maps_basic_json_receipts_without_exposing_credentials(
    tmp_path: Path, monkeypatch
) -> None:
    credential = tmp_path / "oauth.json"
    credentials(credential)
    transport = AppsScriptApiTransport(AppsScriptApiConfig("fixture-deployment", credential))
    monkeypatch.setattr(
        transport,
        "run",
        lambda function, parameters=None: {
            "status": "PREVIEW",
            "sourceVersion": 3,
            "checksum": "a" * 64,
            "confirmationNonce": "nonce",
            "rowCounts": {"CaseBoard": 1},
            "safeResultCode": "SYNC_PREVIEW_READY",
        },
    )
    receipt = transport.preview({"fixture": True})
    assert receipt.source_version == 3
    assert receipt.safe_result_code == "SYNC_PREVIEW_READY"
    assert "fixture-access-token" not in repr(receipt)


def test_transport_requires_sheet_and_send_mail_scopes(tmp_path: Path) -> None:
    credential = tmp_path / "oauth.json"
    credentials(credential)
    transport = AppsScriptApiTransport(AppsScriptApiConfig("fixture-deployment", credential))

    assert set(transport._credentials.scopes or ()) == set(APPS_SCRIPT_SCOPES)  # noqa: SLF001


class FakeResponse:
    def __init__(self, body: dict[str, object]) -> None:
        self.body = body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.body).encode("utf-8")


def test_transport_preserves_safe_gas_execution_error(tmp_path: Path, monkeypatch) -> None:
    credential = tmp_path / "oauth.json"
    credentials(credential)
    transport = AppsScriptApiTransport(AppsScriptApiConfig("fixture-deployment", credential))
    monkeypatch.setattr(transport, "_access_token", lambda: "fixture-access-token")
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(
            {
                "done": True,
                "error": {
                    "code": 3,
                    "message": "ScriptError",
                    "details": [
                        {
                            "errorType": "ScriptError",
                            "errorMessage": "Error: BRIDGE_TARGET_NOT_CONFIGURED",
                        }
                    ],
                },
            }
        ),
    )

    with pytest.raises(AppsScriptApiError, match="BRIDGE_TARGET_NOT_CONFIGURED"):
        transport.health()


def test_transport_accepts_only_allowlisted_email_receipt(tmp_path: Path, monkeypatch) -> None:
    credential = tmp_path / "oauth.json"
    credentials(credential)
    transport = AppsScriptApiTransport(AppsScriptApiConfig("fixture-deployment", credential))
    monkeypatch.setattr(
        transport,
        "run",
        lambda _function, _parameters=None: {
            "deliveryId": "email_delivery_12345678",
            "status": "PROVIDER_ACCEPTED",
            "safeResultCode": "EMAIL_PROVIDER_ACCEPTED",
            "quotaRemainingBefore": 50,
        },
    )
    receipt = transport.send_verification_email({"fixture": True})
    assert receipt["safeResultCode"] == "EMAIL_PROVIDER_ACCEPTED"

    monkeypatch.setattr(
        transport,
        "run",
        lambda _function, _parameters=None: {
            "deliveryId": "email_delivery_12345678",
            "status": "PROVIDER_ACCEPTED",
            "safeResultCode": "EMAIL_PROVIDER_ACCEPTED",
            "quotaRemainingBefore": 50,
            "destination": "student@example.com",
        },
    )
    with pytest.raises(AppsScriptApiError, match="EMAIL_DELIVERY_RECEIPT_INVALID"):
        transport.send_verification_email({"fixture": True})
