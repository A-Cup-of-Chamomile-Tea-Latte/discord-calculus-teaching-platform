"""Fail-closed conversion from Discord snapshots to the CaseMessage contract."""

from __future__ import annotations

from bots.archive_reader.models import ArchiveAttachmentMetadata, ArchiveMessageRecord
from bots.archive_reader.repositories import MessageIdentityPolicyRepository
from bots.common.config import SNOWFLAKE_PATTERN
from bots.common.contracts import ContractRegistry
from bots.common.errors import ContractValidationError, ResourceNotFoundError
from bots.common.models import DiscordMessageSnapshot


def internal_message_id(discord_message_id: str) -> str:
    if not SNOWFLAKE_PATTERN.fullmatch(discord_message_id):
        raise ContractValidationError("Discord message ID is invalid.")
    return f"msg_discord_{discord_message_id}"


class ArchiveMessageMapper:
    def __init__(
        self,
        identities: MessageIdentityPolicyRepository,
        contracts: ContractRegistry,
    ) -> None:
        self._identities = identities
        self._contracts = contracts

    def map(self, case_id: str, snapshot: DiscordMessageSnapshot) -> ArchiveMessageRecord:
        if not snapshot.content:
            raise ContractValidationError(
                "Attachment-only Discord messages need an explicit product mapping policy."
            )
        identity = self._identities.get_by_discord_user_id(snapshot.author_id)
        if identity is None:
            raise ResourceNotFoundError(
                "A Discord author has no approved internal identity/export policy."
            )
        attachments = tuple(
            ArchiveAttachmentMetadata(
                attachment_id=f"attachment_discord_{attachment.attachment_id}",
                filename=attachment.filename,
                media_type=attachment.content_type or "application/octet-stream",
                size_bytes=attachment.size_bytes,
            )
            for attachment in snapshot.attachments
        )
        record = ArchiveMessageRecord(
            message_id=internal_message_id(snapshot.message_id),
            case_id=case_id,
            author_user_id=identity.author_user_id,
            author_role=identity.author_role,
            author_display_mode=identity.author_display_mode,
            body=snapshot.content,
            analysis_permission=identity.analysis_permission,
            parent_message_id=(
                internal_message_id(snapshot.parent_message_id)
                if snapshot.parent_message_id is not None
                else None
            ),
            discord_message_id=snapshot.message_id,
            edited_at=snapshot.edited_at,
            attachments=attachments,
            created_at=snapshot.created_at,
        )
        self._contracts.validate("case-message.schema.json", record.to_contract())
        return record
