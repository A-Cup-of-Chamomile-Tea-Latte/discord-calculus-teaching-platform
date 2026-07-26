"""Discord modal adapter for identity-safe anonymous replies."""

from __future__ import annotations

from typing import Protocol, cast

import discord

from bots.common.errors import (
    AuthorizationError,
    ConflictError,
    NotConfiguredError,
    ResourceNotFoundError,
)
from bots.course_assistant.models import ActorContext, AnonymousReplyCommand
from bots.course_assistant.service import CourseAssistantService

EXPECTED_INTERACTION_ERRORS = (
    AuthorizationError,
    ConflictError,
    NotConfiguredError,
    ResourceNotFoundError,
    ValueError,
)


class InteractionIdentityResolver(Protocol):
    """Maps a Discord identity to an already-authenticated internal actor."""

    def resolve(self, discord_user_id: str) -> ActorContext | None: ...


class InMemoryInteractionIdentityResolver:
    def __init__(self, seed: dict[str, ActorContext] | None = None) -> None:
        self._actors = dict(seed or {})

    def resolve(self, discord_user_id: str) -> ActorContext | None:
        return self._actors.get(discord_user_id)


class AnonymousReplyModal(discord.ui.Modal):
    def __init__(self, adapter: AnonymousReplyDiscordAdapter, case_id: str) -> None:
        super().__init__(
            title="匿名回覆",
            timeout=300,
            custom_id=f"anonymous_reply:{case_id}",
        )
        self._adapter = adapter
        self._case_id = case_id
        self.body_input: discord.ui.TextInput[AnonymousReplyModal] = discord.ui.TextInput(
            style=discord.TextStyle.paragraph,
            custom_id="anonymous_reply_body",
            placeholder="請輸入要由機器人代為發布的回覆",
            required=True,
            min_length=1,
            max_length=1800,
        )
        self.body_label: discord.ui.Label[AnonymousReplyModal] = discord.ui.Label(
            text="回覆內容",
            description="送出前不會在公開頻道出現",
            component=self.body_input,
        )
        self.add_item(self.body_label)

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        await self._adapter.submit_modal(
            interaction,
            case_id=self._case_id,
            body=self.body_input.value,
        )


class AnonymousReplyDiscordAdapter:
    """Thin interaction layer; public posting remains inside the writer service."""

    def __init__(
        self,
        service: CourseAssistantService,
        identities: InteractionIdentityResolver,
    ) -> None:
        self._service = service
        self._identities = identities

    async def open_modal(self, interaction: discord.Interaction, *, case_id: str) -> bool:
        actor = self._resolve_actor(interaction)
        if actor is None:
            await interaction.response.send_message(
                "無法開啟此回覆表單。",
                ephemeral=True,
            )
            return False
        try:
            self._service.authorize_anonymous_reply(actor, case_id)
        except EXPECTED_INTERACTION_ERRORS:
            await interaction.response.send_message(
                "無法開啟此回覆表單。",
                ephemeral=True,
            )
            return False
        await interaction.response.send_modal(AnonymousReplyModal(self, case_id))
        return True

    async def submit_modal(
        self,
        interaction: discord.Interaction,
        *,
        case_id: str,
        body: str,
    ) -> bool:
        actor = self._resolve_actor(interaction)
        if actor is None:
            await interaction.response.send_message(
                "無法發布此回覆。",
                ephemeral=True,
            )
            return False
        try:
            published = await self._service.post_anonymous_reply(
                actor,
                AnonymousReplyCommand(
                    operation_id=f"anonymous-reply:{interaction.id}",
                    case_id=case_id,
                    body=body,
                ),
            )
        except EXPECTED_INTERACTION_ERRORS:
            await interaction.response.send_message(
                "無法發布此回覆。請檢查內容或稍後再試。",
                ephemeral=True,
            )
            return False
        await interaction.response.send_message(
            published.ephemeral_confirmation,
            ephemeral=True,
        )
        return True

    def _resolve_actor(self, interaction: discord.Interaction) -> ActorContext | None:
        discord_user_id = str(interaction.user.id)
        return self._identities.resolve(discord_user_id)


class AnonymousReplyButton(discord.ui.Button[discord.ui.View]):
    def __init__(self, adapter: AnonymousReplyDiscordAdapter, case_id: str) -> None:
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="以案件顯示方式回覆",
            custom_id=f"anonymous_reply_open:{case_id}",
        )
        self._adapter = adapter
        self._case_id = case_id

    async def callback(self, interaction: discord.Interaction, /) -> None:
        await self._adapter.open_modal(interaction, case_id=self._case_id)


class AnonymousReplyView(discord.ui.View):
    def __init__(self, adapter: AnonymousReplyDiscordAdapter, case_id: str) -> None:
        super().__init__(timeout=None)
        self.add_item(AnonymousReplyButton(adapter, case_id))


def modal_text_input(modal: AnonymousReplyModal) -> discord.ui.TextInput[AnonymousReplyModal]:
    """Typed inspection helper used by the fixture demonstration."""
    return cast(discord.ui.TextInput[AnonymousReplyModal], modal.body_label.component)
