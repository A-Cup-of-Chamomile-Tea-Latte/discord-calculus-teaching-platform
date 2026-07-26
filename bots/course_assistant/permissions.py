"""Explicit staff checks and role allowlists."""

from __future__ import annotations

from dataclasses import dataclass

from bots.common.errors import AuthorizationError, NotConfiguredError
from bots.course_assistant.models import ActorContext
from bots.course_assistant.repositories import CLASS_CODE_PATTERN


@dataclass(frozen=True)
class StaffPermissionPolicy:
    staff_user_ids: frozenset[str]
    staff_role_ids: frozenset[str]

    def require_staff(self, actor: ActorContext) -> None:
        if actor.user_id in self.staff_user_ids:
            return
        if self.staff_role_ids.intersection(actor.role_ids):
            return
        raise AuthorizationError("This operation requires teaching-staff authorization.")


@dataclass(frozen=True)
class MembershipRolePolicy:
    broad_membership_role_id: str
    class_role_ids: dict[str, str]

    def roles_for_class(self, class_code: str) -> tuple[str, str]:
        if not CLASS_CODE_PATTERN.fullmatch(class_code):
            raise ValueError("class_code must contain exactly two digits")
        class_role = self.class_role_ids.get(class_code)
        if class_role is None:
            raise NotConfiguredError("No allowlisted Discord role is configured for this class.")
        return self.broad_membership_role_id, class_role
