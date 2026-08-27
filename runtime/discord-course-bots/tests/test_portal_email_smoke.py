from __future__ import annotations

import json
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from discord_course_bots.portal_email_smoke import (
    PortalEmailSmokeError,
    PortalEmailSmokeSettings,
    destination_fingerprint,
    run_email_smoke,
)


class CapturingTransport:
    transport_name = "test-capture"

    def __init__(self) -> None:
        self.delivery: dict[str, object] | None = None

    def send_verification_email(self, delivery: dict[str, object]) -> dict[str, object]:
        self.delivery = dict(delivery)
        return {
            "deliveryId": delivery["deliveryId"],
            "status": "PROVIDER_ACCEPTED",
            "safeResultCode": "EMAIL_PROVIDER_ACCEPTED",
            "quotaRemainingBefore": 100,
        }


def credential(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "token": "fixture-token",
                "refresh_token": "fixture-refresh",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "fixture-client",
                "client_secret": "fixture-secret",
                "scopes": [
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/script.send_mail",
                ],
                "expiry": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    path.chmod(0o600)


def settings(tmp_path: Path, destination: str = "white.account@example.com"):
    oauth = tmp_path / "oauth.json"
    credential(oauth)
    return PortalEmailSmokeSettings(
        root=tmp_path / "isolated",
        destination=destination,
        allowed_destination_hash=destination_fingerprint(destination),
        discord_username="white.account",
        deployment_id="fixture-deployment",
        credential_path=oauth,
    )


def test_controlled_email_smoke_runs_full_chain_and_scrubs_temporary_data(
    tmp_path: Path,
) -> None:
    transport = CapturingTransport()
    progress: list[str] = []

    result = run_email_smoke(
        settings(tmp_path),
        transport,  # type: ignore[arg-type]
        code_reader=lambda: str(transport.delivery["code"]),  # type: ignore[index]
        progress=progress.append,
    )

    assert result == {
        "portalEmailSmoke": "PASS",
        "emailDelivery": "COMPLETED",
        "emailChallenge": "CONSUMED",
        "joinApplication": "PENDING_REVIEW",
        "productionDatabaseModified": "NO",
        "discordMutation": "NO",
        "sensitiveValuesPrinted": "NO",
    }
    assert progress == ["EMAIL_SENT_WAITING_FOR_CODE"]
    assert stat.S_IMODE((tmp_path / "isolated").stat().st_mode) == 0o700


def test_controlled_email_smoke_refuses_destination_or_credential_boundary(
    tmp_path: Path,
) -> None:
    config = settings(tmp_path)
    refused = PortalEmailSmokeSettings(
        root=config.root,
        destination=config.destination,
        allowed_destination_hash="0" * 64,
        discord_username=config.discord_username,
        deployment_id=config.deployment_id,
        credential_path=config.credential_path,
    )
    with pytest.raises(PortalEmailSmokeError, match="DESTINATION_ALLOWLIST_MISMATCH"):
        refused.validate()

    config.credential_path.chmod(0o644)
    with pytest.raises(PortalEmailSmokeError, match="OAUTH_CREDENTIAL_MODE_INVALID"):
        config.validate()
