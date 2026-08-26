from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from discord_course_bots.data_lab.transport import (
    ApplyReceipt,
    PreviewReceipt,
    RemoteCommandClaim,
)

APPS_SCRIPT_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
SAFE_CODE = re.compile(r"[^A-Z0-9_]+")


class AppsScriptApiError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class AppsScriptApiConfig:
    deployment_id: str
    credential_path: Path
    timeout_seconds: int = 30


def _safe_code(value: object, fallback: str) -> str:
    if value is None:
        return fallback
    text = SAFE_CODE.sub("_", str(value).upper()).strip("_")[:64]
    return text or fallback


def _operation_error_code(error: object) -> str:
    if not isinstance(error, dict):
        return "GOOGLE_OPERATION_FAILED"
    status = error.get("status")
    if status:
        return _safe_code(status, "GOOGLE_OPERATION_FAILED")
    details = error.get("details")
    if isinstance(details, list):
        for detail in details:
            if isinstance(detail, dict) and detail.get("errorMessage"):
                message = str(detail["errorMessage"])
                if message.startswith("Error: "):
                    message = message.removeprefix("Error: ")
                return _safe_code(message, "GAS_EXECUTION_FAILED")
    return _safe_code(error.get("message"), "GAS_EXECUTION_FAILED")


class AppsScriptApiTransport:
    is_cloud = True
    transport_name = "APPS_SCRIPT_API"

    def __init__(self, config: AppsScriptApiConfig) -> None:
        self.config = config
        self._credentials = Credentials.from_authorized_user_file(
            str(config.credential_path), [APPS_SCRIPT_SCOPE]
        )

    def _access_token(self) -> str:
        expiry = self._credentials.expiry
        needs_refresh = (
            not self._credentials.valid
            or expiry is None
            or expiry.astimezone(UTC) <= datetime.now(UTC) + timedelta(minutes=6)
        )
        if needs_refresh:
            try:
                self._credentials.refresh(Request())
            except Exception as error:
                raise AppsScriptApiError("OAUTH_REFRESH_FAILED") from error
        token = self._credentials.token
        if not token:
            raise AppsScriptApiError("OAUTH_ACCESS_TOKEN_MISSING")
        return token

    def run(self, function: str, parameters: list[Any] | None = None) -> Any:
        payload = json.dumps(
            {"function": function, "parameters": parameters or [], "devMode": False},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        request = urllib.request.Request(
            f"https://script.googleapis.com/v1/scripts/{self.config.deployment_id}:run",
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._access_token()}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(  # noqa: S310 - fixed Google API endpoint
                request, timeout=self.config.timeout_seconds
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code in {401, 403}:
                raise AppsScriptApiError("GOOGLE_AUTHORIZATION_REFUSED") from error
            if error.code == 404:
                raise AppsScriptApiError("GOOGLE_DEPLOYMENT_NOT_FOUND") from error
            if error.code == 429:
                raise AppsScriptApiError("GOOGLE_RATE_LIMITED") from error
            raise AppsScriptApiError(f"GOOGLE_HTTP_{error.code}") from error
        except (OSError, TimeoutError, json.JSONDecodeError) as error:
            raise AppsScriptApiError("GOOGLE_TRANSPORT_UNAVAILABLE") from error

        if "error" in body:
            raise AppsScriptApiError(_operation_error_code(body["error"]))
        operation = body.get("response", {})
        if "error" in operation:
            details = operation["error"].get("details", [])
            message = details[0].get("errorMessage") if details else None
            raise AppsScriptApiError(_safe_code(message, "GAS_EXECUTION_FAILED"))
        return operation.get("result")

    def health(self) -> dict[str, Any]:
        result = self.run("bridgeHealth")
        if not isinstance(result, dict):
            raise AppsScriptApiError("BRIDGE_HEALTH_INVALID")
        return result

    def preview(self, envelope: dict[str, Any]) -> PreviewReceipt:
        result = self.run("bridgePreview", [envelope])
        if not isinstance(result, dict):
            raise AppsScriptApiError("BRIDGE_PREVIEW_INVALID")
        return PreviewReceipt(
            str(result["status"]),
            int(result["sourceVersion"]),
            str(result["checksum"]),
            str(result["confirmationNonce"]),
            {str(key): int(value) for key, value in result["rowCounts"].items()},
            str(result["safeResultCode"]),
        )

    def apply(self, envelope: dict[str, Any], confirmation_nonce: str) -> ApplyReceipt:
        result = self.run("bridgeApply", [envelope, confirmation_nonce])
        if not isinstance(result, dict):
            raise AppsScriptApiError("BRIDGE_APPLY_INVALID")
        return ApplyReceipt(
            str(result["status"]),
            int(result["sourceVersion"]),
            str(result["checksum"]),
            str(result["safeResultCode"]),
        )

    def preview_commands(self, limit: int = 1) -> list[dict[str, Any]]:
        result = self.run("bridgePeekCommands", [limit])
        if result is None:
            return []
        if not isinstance(result, list):
            raise AppsScriptApiError("COMMAND_PREVIEW_INVALID")
        return [dict(value) for value in result]

    def claim_command(self, worker_id: str, **_: Any) -> RemoteCommandClaim | None:
        result = self.run("bridgeClaimCommand", [worker_id])
        if result is None:
            return None
        if not isinstance(result, dict):
            raise AppsScriptApiError("COMMAND_CLAIM_INVALID")
        return RemoteCommandClaim(
            dict(result["envelope"]),
            str(result["claimToken"]),
            str(result["leaseExpiresAt"]),
        )

    def ack_command(self, command_id: str, claim_token: str, result_code: str) -> bool:
        return bool(self.run("bridgeAckCommand", [command_id, claim_token, result_code]))

    def send_verification_email(self, delivery: dict[str, Any]) -> dict[str, Any]:
        result = self.run("bridgeSendVerificationEmail", [delivery])
        if not isinstance(result, dict):
            raise AppsScriptApiError("EMAIL_DELIVERY_RECEIPT_INVALID")
        allowed = {
            "deliveryId",
            "status",
            "safeResultCode",
            "quotaRemainingBefore",
        }
        if set(result) != allowed:
            raise AppsScriptApiError("EMAIL_DELIVERY_RECEIPT_INVALID")
        if result.get("status") not in {"PROVIDER_ACCEPTED", "NO_OP"}:
            raise AppsScriptApiError("EMAIL_DELIVERY_RECEIPT_INVALID")
        return dict(result)
