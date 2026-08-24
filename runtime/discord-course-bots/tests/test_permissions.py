from types import SimpleNamespace
from unittest.mock import MagicMock

from discord_course_bots.course_assistant.service import CourseService
from discord_course_bots.invites import COURSE_ASSISTANT_PERMISSIONS, DUMP_BOT_PERMISSIONS


def test_course_assistant_forbidden_permissions_absent() -> None:
    forbidden = {
        "administrator": 8,
        "manage_guild": 32,
        "kick_members": 2,
        "ban_members": 4,
        "mention_everyone": 131072,
        "manage_webhooks": 536870912,
    }
    assert all(COURSE_ASSISTANT_PERMISSIONS & bit == 0 for bit in forbidden.values())


def test_dump_bot_is_read_only_permission_pair() -> None:
    assert DUMP_BOT_PERMISSIONS == 1024 | 65536


def test_configured_system_admin_role_grants_operator_access() -> None:
    settings = SimpleNamespace(owner_ids=frozenset())
    repository = MagicMock()
    repository.reviewer_level.return_value = None
    repository.get_config_int.return_value = 700
    service = CourseService(MagicMock(), settings, repository)
    member = SimpleNamespace(id=42, roles=[SimpleNamespace(id=700)])

    assert service.is_allowed_operator(member)
    repository.get_config_int.assert_called_once_with("system_admin_role_id")
