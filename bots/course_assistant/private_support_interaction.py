"""Private modal entrypoint backed only by the restricted Private Support service."""

from __future__ import annotations

import discord

from bots.common.errors import (
    AuthorizationError,
    ConflictError,
    ResourceNotFoundError,
)
from bots.course_assistant.anonymous_reply import InteractionIdentityResolver
from bots.course_assistant.private_support import (
    CreatePrivateSupportCommand,
    PrivateSupportService,
    PrivateSupportSource,
)

EXPECTED_PRIVATE_SUPPORT_ERRORS = (
    AuthorizationError,
    ConflictError,
    ResourceNotFoundError,
    ValueError,
)


class PrivateSupportModal(discord.ui.Modal):
    def __init__(self, adapter: PrivateSupportDiscordAdapter) -> None:
        super().__init__(
            title="Private Support",
            timeout=300,
            custom_id="private_support_create",
        )
        self._adapter = adapter
        self.title_input: discord.ui.TextInput[PrivateSupportModal] = discord.ui.TextInput(
            custom_id="private_support_title",
            placeholder="請用簡短主旨描述你需要的協助",
            required=True,
            min_length=1,
            max_length=160,
        )
        self.body_input: discord.ui.TextInput[PrivateSupportModal] = discord.ui.TextInput(
            style=discord.TextStyle.paragraph,
            custom_id="private_support_body",
            placeholder="這些內容不會進入公開案件查詢或教學分析",
            required=True,
            min_length=1,
            max_length=1800,
        )
        self.add_item(
            discord.ui.Label(
                text="主旨",
                description="只對你與經授權的教學團隊顯示",
                component=self.title_input,
            )
        )
        self.add_item(
            discord.ui.Label(
                text="需要的協助",
                description="不會產生公開案件編號",
                component=self.body_input,
            )
        )

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        await self._adapter.submit_modal(
            interaction,
            title=self.title_input.value,
            body=self.body_input.value,
        )


class PrivateSupportDiscordAdapter:
    def __init__(
        self,
        service: PrivateSupportService,
        identities: InteractionIdentityResolver,
    ) -> None:
        self._service = service
        self._identities = identities

    async def open_modal(self, interaction: discord.Interaction) -> bool:
        actor = self._identities.resolve(str(interaction.user.id))
        if actor is None:
            await interaction.response.send_message(
                "無法開啟 Private Support。",
                ephemeral=True,
            )
            return False
        await interaction.response.send_modal(PrivateSupportModal(self))
        return True

    async def submit_modal(
        self,
        interaction: discord.Interaction,
        *,
        title: str,
        body: str,
    ) -> bool:
        actor = self._identities.resolve(str(interaction.user.id))
        if actor is None:
            await interaction.response.send_message(
                "無法建立 Private Support。",
                ephemeral=True,
            )
            return False
        try:
            await self._service.create(
                actor,
                CreatePrivateSupportCommand(
                    operation_id=f"private-support:{interaction.id}",
                    case_id=f"case_private_{interaction.id}",
                    source=PrivateSupportSource.BOT,
                    title=title,
                    body=body,
                ),
            )
        except EXPECTED_PRIVATE_SUPPORT_ERRORS:
            await interaction.response.send_message(
                "無法建立 Private Support。請檢查內容或稍後再試。",
                ephemeral=True,
            )
            return False
        await interaction.response.send_message(
            "Private Support 已建立；它不會出現在公開案件查詢或教學分析。",
            ephemeral=True,
        )
        return True


class PrivateSupportButton(discord.ui.Button[discord.ui.View]):
    def __init__(self, adapter: PrivateSupportDiscordAdapter) -> None:
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="開啟 Private Support",
            custom_id="private_support_open",
        )
        self._adapter = adapter

    async def callback(self, interaction: discord.Interaction, /) -> None:
        await self._adapter.open_modal(interaction)


class PrivateSupportView(discord.ui.View):
    def __init__(self, adapter: PrivateSupportDiscordAdapter) -> None:
        super().__init__(timeout=None)
        self.add_item(PrivateSupportButton(adapter))
