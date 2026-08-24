from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from discord_course_bots.course_assistant.service import CaseAlreadyOpenError
from discord_course_bots.course_assistant.views import AIPermissionView, ReopenView


@pytest.mark.asyncio
async def test_successful_reopen_disables_its_closure_button() -> None:
    service = MagicMock()
    service.interaction_retry_after.return_value = None
    service.claim_reopen.return_value = {"case_id": "case-1"}
    view = ReopenView(service)
    reopen_button = view.children[0]
    channel = MagicMock(spec=discord.Thread)
    message = SimpleNamespace(edit=AsyncMock())
    interaction = SimpleNamespace(
        channel=channel,
        user=SimpleNamespace(id=3),
        message=message,
        response=SimpleNamespace(defer=AsyncMock(), send_message=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )

    await reopen_button.callback(interaction)

    service.claim_reopen.assert_called_once_with(3, channel.id)
    assert reopen_button.disabled is True
    message.edit.assert_awaited_once_with(view=view)
    interaction.response.send_message.assert_awaited_once_with(
        "已收到；案件正在重新開啟。完成後會在討論串通知您。",
        ephemeral=True,
    )
    interaction.response.defer.assert_not_awaited()
    interaction.followup.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_stale_reopen_button_replies_without_thinking() -> None:
    message_text = "案件目前已經開啟；請先繼續提問，待再次結案後才能重新開啟下一輪。"
    service = MagicMock()
    service.interaction_retry_after.return_value = None
    service.claim_reopen.side_effect = CaseAlreadyOpenError(message_text)
    view = ReopenView(service)
    reopen_button = view.children[0]
    channel = MagicMock(spec=discord.Thread)
    interaction = SimpleNamespace(
        channel=channel,
        user=SimpleNamespace(id=3),
        message=SimpleNamespace(edit=AsyncMock()),
        response=SimpleNamespace(defer=AsyncMock(), send_message=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )

    await reopen_button.callback(interaction)

    interaction.response.send_message.assert_awaited_once_with(message_text, ephemeral=True)
    interaction.response.defer.assert_not_awaited()
    interaction.followup.send.assert_not_awaited()
    assert reopen_button.disabled is False


@pytest.mark.asyncio
async def test_reopen_throttle_rejects_before_repository_work() -> None:
    service = MagicMock()
    service.interaction_retry_after.return_value = 5
    view = ReopenView(service)
    reopen_button = view.children[0]
    channel = MagicMock(spec=discord.Thread)
    interaction = SimpleNamespace(
        channel=channel,
        user=SimpleNamespace(id=3),
        message=SimpleNamespace(edit=AsyncMock()),
        response=SimpleNamespace(defer=AsyncMock(), send_message=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )

    await reopen_button.callback(interaction)

    service.claim_reopen.assert_not_called()
    interaction.response.send_message.assert_awaited_once_with(
        "操作太頻繁，請約 5 秒後再試。", ephemeral=True
    )


@pytest.mark.asyncio
async def test_ai_permission_uses_yes_no_buttons_instead_of_a_select() -> None:
    view = AIPermissionView(MagicMock(), thread_id=1, author_id=3, keyword="test")
    labels = [child.label for child in view.children if isinstance(child, discord.ui.Button)]
    assert labels == ["允許", "不允許", "完成設定", "取消"]
    assert not any(isinstance(child, discord.ui.Select) for child in view.children)

    interaction = SimpleNamespace(
        user=SimpleNamespace(id=3),
        response=SimpleNamespace(edit_message=AsyncMock(), send_message=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )
    yes_button = next(child for child in view.children if child.label == "允許")
    await yes_button.callback(interaction)

    assert view.ai_permission is True
    assert yes_button.style is discord.ButtonStyle.success
    interaction.response.edit_message.assert_awaited_once_with(
        content="AI 文字內容分析：**允許**", view=view
    )
