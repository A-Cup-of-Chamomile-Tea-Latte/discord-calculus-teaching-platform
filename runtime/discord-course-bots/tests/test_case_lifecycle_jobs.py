from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from discord_course_bots.course_assistant.cogs import CaseCog
from discord_course_bots.course_assistant.service import CourseService, PrivateDumpPending
from discord_course_bots.repository import Repository


def _case(repo: Repository, *, status: str = "TRACKED") -> None:
    repo.create_case(
        case_id="case-1",
        thread_id=1,
        author_id=3,
        module_code="M1",
        keyword="test",
        ai_content_permission=False,
        canonical_title="[M1] [test] Question",
        initial_snapshot={"body": "hello"},
        class_code="01",
    )
    assert repo.claim_case(1, 9) is not None
    if status == "CLOSED":
        repo.close_case(1)
        claim = repo.claim_discord_lifecycle_job("setup")
        assert claim is not None
        assert repo.complete_discord_lifecycle_job(claim.job_id, claim.claim_token)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("forum_id", "managed"),
    [(101, True), (102, True), (103, True), (999, False)],
)
async def test_public_case_registration_covers_all_three_managed_forums(
    tmp_path: Path, forum_id: int, managed: bool
) -> None:
    repo = Repository(tmp_path / f"forum-{forum_id}.sqlite3")
    repo.set_config("managed_forum_ids", "[101, 102, 103]")
    starter = SimpleNamespace(id=forum_id + 2000, author=SimpleNamespace(id=3))
    setup = SimpleNamespace(id=forum_id + 3000)
    thread = MagicMock(spec=discord.Thread)
    thread.id = forum_id + 1000
    thread.parent_id = forum_id
    thread.guild.id = 10
    thread.name = "同批 forum 測試"
    thread.fetch_message = AsyncMock(return_value=starter)
    thread.send = AsyncMock(return_value=setup)
    settings = MagicMock(test_guild_id=10)
    service = CourseService(MagicMock(), settings, repo)

    await service.register_new_thread(thread)

    draft = repo.get_draft(thread.id)
    if managed:
        assert draft is not None
        assert int(draft["forum_channel_id"]) == forum_id
        thread.send.assert_awaited_once()
    else:
        assert draft is None
        thread.send.assert_not_awaited()


def test_guest_public_identity_is_distinct_from_class_roles(tmp_path: Path) -> None:
    repo = Repository(tmp_path / "guest-identity.sqlite3")
    repo.set_config("visitor_role_id", 700)
    repo.set_config("class_role_01", 101)
    repo.set_config("class_module_01", "M1")
    settings = MagicMock()
    settings.module_code = "M1"
    service = CourseService(MagicMock(), settings, repo)
    guest = MagicMock(spec=discord.Member)
    guest.roles = [SimpleNamespace(id=700)]
    conflict = MagicMock(spec=discord.Member)
    conflict.roles = [SimpleNamespace(id=700), SimpleNamespace(id=101)]

    assert service.public_case_context_for_member(guest) == (None, "M1", True)
    with pytest.raises(RuntimeError, match="同時存在"):
        service.public_case_context_for_member(conflict)


@pytest.mark.asyncio
async def test_close_job_records_notice_before_one_combined_thread_edit(tmp_path: Path) -> None:
    repo = Repository(tmp_path / "close.sqlite3")
    _case(repo)
    assert repo.close_case(1) is not None
    claim = repo.claim_discord_lifecycle_job("worker")
    assert claim is not None

    notice = SimpleNamespace(id=99)
    thread = MagicMock(spec=discord.Thread)
    thread.id = 1
    thread.send = AsyncMock(return_value=notice)
    thread.edit = AsyncMock()
    bot = MagicMock()
    bot.get_channel.return_value = thread
    service = CourseService(bot, MagicMock(), repo)

    await service.apply_discord_lifecycle_job(claim)

    thread.send.assert_awaited_once()
    thread.edit.assert_awaited_once_with(
        name="✅ [M1] [test] Question",
        archived=True,
        locked=False,
        reason="Course case closed",
    )
    job = repo.get_discord_lifecycle_job(claim.job_id)
    assert job is not None
    assert job["stage"] == "NOTICE_SENT"
    assert job["control_message_id"] == 99


@pytest.mark.asyncio
async def test_reopen_job_is_restart_safe_after_public_notice(tmp_path: Path) -> None:
    repo = Repository(tmp_path / "reopen.sqlite3")
    _case(repo, status="CLOSED")
    repo.set_case_jump_url(1, "https://discord.com/channels/1/1")
    reopened = repo.reopen_case(1)
    assert reopened is not None
    claim = repo.claim_discord_lifecycle_job("worker")
    assert claim is not None

    notice = SimpleNamespace(id=100)
    thread = MagicMock(spec=discord.Thread)
    thread.id = 1
    thread.send = AsyncMock(return_value=notice)
    thread.edit = AsyncMock()
    bot = MagicMock()
    bot.get_channel.return_value = thread
    service = CourseService(bot, MagicMock(), repo)

    await service.apply_discord_lifecycle_job(claim)
    await service.apply_discord_lifecycle_job(claim)

    thread.edit.assert_awaited_once_with(
        archived=False,
        locked=False,
        name="[M1] [test] Question 2",
        reason="Course case reopened",
    )
    thread.send.assert_awaited_once_with(
        "🔄 **第 2 次提問已開始 / Round 2 started.** "
        "請繼續提出問題。 / Please continue with your question."
    )
    reopened_dm = repo.get_dm_message("case-reopen:case-1:2")
    assert reopened_dm is not None
    assert reopened_dm["message_kind"] == "CASE_REOPENED"


@pytest.mark.asyncio
async def test_ops_status_is_owner_only_and_ephemeral() -> None:
    service = MagicMock()
    service.settings.test_guild_id = 10
    service.is_allowed_operator.return_value = False
    cog = CaseCog(MagicMock(), service)
    member = MagicMock(spec=discord.Member)
    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=10),
        user=member,
        response=SimpleNamespace(is_done=lambda: False, send_message=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )

    await cog.ops_status.callback(cog, interaction)

    service.repo.safe_runtime_status.assert_not_called()
    interaction.response.send_message.assert_awaited_once_with(
        "只有本伺服器的系統管理者可以執行此操作。", ephemeral=True
    )


def _auto_closed_private(repo: Repository) -> object:
    opened = repo.begin_private_open_request(
        interaction_id="private-1",
        guild_id=10,
        requester_id=3,
        ai_content_permission=True,
    )
    assert opened["status"] == "PENDING"
    repo.complete_private_open_request(
        interaction_id="private-1",
        channel_id=55,
        jump_url="https://discord.com/channels/10/55",
        requester_id=3,
        ai_content_permission=True,
    )
    moment = datetime.now(UTC) + timedelta(seconds=1)
    repo.record_case_activity(55, actor_id=9, is_staff=True, occurred_at=moment)
    repo.mark_due_cases_idle(48 * 3600, now=moment + timedelta(hours=48, seconds=1))
    idle_claim = repo.claim_discord_lifecycle_job("idle-worker")
    assert idle_claim is not None
    assert repo.complete_discord_lifecycle_job(idle_claim.job_id, idle_claim.claim_token)
    repo.auto_close_due_cases(48 * 3600, now=moment + timedelta(hours=96, seconds=2))
    lifecycle_claim = repo.claim_discord_lifecycle_job("close-worker")
    assert lifecycle_claim is not None
    return lifecycle_claim


def _manually_closed_private(repo: Repository) -> object:
    repo.begin_private_open_request(
        interaction_id="private-manual",
        guild_id=10,
        requester_id=3,
        ai_content_permission=True,
    )
    repo.complete_private_open_request(
        interaction_id="private-manual",
        channel_id=56,
        jump_url="https://discord.com/channels/10/56",
        requester_id=3,
        ai_content_permission=True,
    )
    moment = datetime.now(UTC) + timedelta(seconds=1)
    repo.record_case_activity(56, actor_id=9, is_staff=True, occurred_at=moment)
    assert repo.close_case(56, now=moment) is not None
    close_claim = repo.claim_discord_lifecycle_job("manual-close-worker")
    assert close_claim is not None
    assert repo.get_discord_lifecycle_job(close_claim.job_id)["transition"] == "CLOSE"
    assert repo.complete_discord_lifecycle_job(close_claim.job_id, close_claim.claim_token)

    assert not repo.auto_close_due_cases(48 * 3600, now=moment + timedelta(hours=47, minutes=59))
    assert repo.get_case_by_thread(56)["status"] == "CLOSED"
    changed = repo.auto_close_due_cases(48 * 3600, now=moment + timedelta(hours=48, seconds=1))
    assert len(changed) == 1
    assert repo.get_case_by_thread(56)["status"] == "AUTO_CLOSED"
    lifecycle_claim = repo.claim_discord_lifecycle_job("manual-retention-worker")
    assert lifecycle_claim is not None
    assert repo.get_discord_lifecycle_job(lifecycle_claim.job_id)["transition"] == "AUTO_CLOSE"
    return lifecycle_claim


@pytest.mark.asyncio
async def test_private_auto_close_waits_for_verified_dump_then_deletes_and_scrubs(
    tmp_path: Path,
) -> None:
    repo = Repository(tmp_path / "private-auto-close.sqlite3")
    lifecycle_claim = _auto_closed_private(repo)
    requester = MagicMock(spec=discord.Member)
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 55
    channel.guild.get_member.return_value = requester
    channel.overwrites_for.return_value = discord.PermissionOverwrite(send_messages=True)
    channel.set_permissions = AsyncMock()
    channel.send = AsyncMock(return_value=SimpleNamespace(id=505))
    channel.delete = AsyncMock()
    bot = MagicMock()
    bot.get_channel.return_value = channel
    service = CourseService(bot, MagicMock(), repo)

    with pytest.raises(PrivateDumpPending):
        await service.apply_discord_lifecycle_job(lifecycle_claim)
    assert not channel.delete.await_count
    channel.set_permissions.assert_awaited_once()
    dump_claim = repo.claim_private_dump_job(worker_id="dump-worker")
    assert dump_claim is not None

    assert repo.complete_private_dump(55, dump_claim.claim_token, "manifest.json")
    await service.apply_discord_lifecycle_job(lifecycle_claim)

    channel.delete.assert_awaited_once()
    case = repo.get_case_by_thread(55)
    assert case["author_id"] == 0
    assert case["initial_snapshot_json"] == "{}"
    assert case["jump_url"] is None
    assert repo.get_private_support(55)["status"] == "DELETED"
    assert repo.get_private_dump_job(55)["status"] == "DELETED"


@pytest.mark.asyncio
async def test_manually_closed_private_waits_48_hours_then_uses_verified_dump(
    tmp_path: Path,
) -> None:
    repo = Repository(tmp_path / "private-manual-close.sqlite3")
    lifecycle_claim = _manually_closed_private(repo)
    requester = MagicMock(spec=discord.Member)
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 56
    channel.guild.get_member.return_value = requester
    channel.overwrites_for.return_value = discord.PermissionOverwrite(send_messages=True)
    channel.set_permissions = AsyncMock()
    channel.send = AsyncMock(return_value=SimpleNamespace(id=506))
    channel.delete = AsyncMock()
    bot = MagicMock()
    bot.get_channel.return_value = channel
    service = CourseService(bot, MagicMock(), repo)

    with pytest.raises(PrivateDumpPending):
        await service.apply_discord_lifecycle_job(lifecycle_claim)
    dump_claim = repo.claim_private_dump_job(worker_id="dump-worker")
    assert dump_claim is not None
    assert repo.complete_private_dump(56, dump_claim.claim_token, "manifest.json")
    await service.apply_discord_lifecycle_job(lifecycle_claim)

    channel.delete.assert_awaited_once()
    assert repo.get_private_support(56)["status"] == "DELETED"


@pytest.mark.asyncio
async def test_stale_private_auto_close_job_cannot_delete_a_reopened_case(tmp_path: Path) -> None:
    repo = Repository(tmp_path / "private-stale-auto-close.sqlite3")
    lifecycle_claim = _auto_closed_private(repo)
    reopened = repo.record_case_activity(55, actor_id=3, is_staff=False)
    assert reopened is not None
    assert reopened["status"] == "TRACKED"
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    channel.delete = AsyncMock()
    bot = MagicMock()
    bot.get_channel.return_value = channel
    service = CourseService(bot, MagicMock(), repo)

    await service.apply_discord_lifecycle_job(lifecycle_claim)

    channel.send.assert_not_awaited()
    channel.delete.assert_not_awaited()
    assert repo.get_private_dump_job(55) is None
