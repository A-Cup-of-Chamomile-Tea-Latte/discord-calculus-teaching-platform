from __future__ import annotations

import json
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from discord_course_bots.apps_script_transport import (
    APPS_SCRIPT_SCOPE,
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
                "scopes": [APPS_SCRIPT_SCOPE],
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
