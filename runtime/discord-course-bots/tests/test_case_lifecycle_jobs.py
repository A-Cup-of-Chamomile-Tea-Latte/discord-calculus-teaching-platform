from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from discord_course_bots.course_assistant.cogs import CaseCog
from discord_course_bots.course_assistant.service import CourseService
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
    )
    assert repo.claim_case(1, 9) is not None
    if status == "CLOSED":
        repo.close_case(1)
        claim = repo.claim_discord_lifecycle_job("setup")
        assert claim is not None
        assert repo.complete_discord_lifecycle_job(claim.job_id, claim.claim_token)


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
    thread.send.assert_awaited_once_with("🔄 **第 2 次提問已開始。** 請繼續提出問題。")


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
        "只有本伺服器的系統管理者可以查看狀態。", ephemeral=True
    )
