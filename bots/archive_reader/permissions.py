"""Fail-closed manager authorization for archive exports."""

from __future__ import annotations

import re
from dataclasses import dataclass

from bots.archive_reader.models import ManagerContext
from bots.common.config import SNOWFLAKE_PATTERN
from bots.common.errors import AuthorizationError

RECORD_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")


@dataclass(frozen=True)
class ManagerAuthorizationPolicy:
    allowed_user_ids: frozenset[str]
    allowed_role_ids: frozenset[str]

    def __post_init__(self) -> None:
        if not self.allowed_user_ids and not self.allowed_role_ids:
            raise ValueError("At least one manager user or role must be allowlisted")
        if any(not RECORD_ID_PATTERN.fullmatch(value) for value in self.allowed_user_ids):
            raise ValueError("Manager user allowlist contains an invalid internal user ID")
        if any(not SNOWFLAKE_PATTERN.fullmatch(value) for value in self.allowed_role_ids):
            raise ValueError("Manager role allowlist contains an invalid Discord role ID")

    def require_manager(self, actor: ManagerContext) -> None:
        if not RECORD_ID_PATTERN.fullmatch(actor.user_id):
            raise AuthorizationError("The archive manager identity is invalid.")
        if actor.user_id in self.allowed_user_ids:
            return
        if self.allowed_role_ids.intersection(actor.role_ids):
            return
        raise AuthorizationError("Archive export requires an allowlisted manager.")
