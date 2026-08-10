from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import discord


@dataclass(slots=True)
class ExportedAttachment:
    id: int
    filename: str
    content_type: str | None
    size: int
    url: str


@dataclass(slots=True)
class ExportedMessage:
    id: int
    author_id: int
    author_display: str
    created_at: str
    edited_at: str | None
    content: str
    reference_message_id: int | None
    attachments: list[ExportedAttachment]


async def collect_messages(channel: "discord.abc.Messageable") -> list[ExportedMessage]:
    messages: list[ExportedMessage] = []
    async for message in channel.history(limit=None, oldest_first=True):
        reference_id = None
        if message.reference is not None:
            reference_id = message.reference.message_id
        messages.append(
            ExportedMessage(
                id=message.id,
                author_id=message.author.id,
                author_display=str(message.author),
                created_at=message.created_at.isoformat(),
                edited_at=None if message.edited_at is None else message.edited_at.isoformat(),
                content=message.content,
                reference_message_id=reference_id,
                attachments=[
                    ExportedAttachment(
                        id=attachment.id,
                        filename=attachment.filename,
                        content_type=attachment.content_type,
                        size=attachment.size,
                        url=attachment.url,
                    )
                    for attachment in message.attachments
                ],
            )
        )
    return messages


def _markdown(channel_id: int, channel_name: str, messages: list[ExportedMessage]) -> str:
    lines = [
        f"# Discord export: {channel_name}",
        "",
        f"- Channel ID: `{channel_id}`",
        f"- Exported at: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Message count: `{len(messages)}`",
        "",
    ]
    for message in messages:
        lines.extend(
            [
                f"## {message.created_at} — {message.author_display} (`{message.author_id}`)",
                "",
                message.content or "*(no text content)*",
                "",
            ]
        )
        if message.reference_message_id is not None:
            lines.append(f"Reply to: `{message.reference_message_id}`\n")
        for attachment in message.attachments:
            lines.append(
                f"- Attachment: `{attachment.filename}` ({attachment.size} bytes) — {attachment.url}"
            )
        if message.attachments:
            lines.append("")
    return "\n".join(lines)


def write_export(
    *,
    output_dir: Path,
    guild_id: int,
    channel_id: int,
    channel_name: str,
    messages: list[ExportedMessage],
    export_scope: str = "unspecified",
    case_number: str | None = None,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"discord-{guild_id}-{channel_id}"
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"
    manifest_path = output_dir / f"{stem}.manifest.json"

    payload: dict[str, Any] = {
        "schema_version": 1,
        "guild_id": guild_id,
        "channel_id": channel_id,
        "channel_name": channel_name,
        "export_scope": export_scope,
        "case_number": case_number,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "message_count": len(messages),
        "messages": [asdict(message) for message in messages],
    }
    json_bytes = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    md_bytes = _markdown(channel_id, channel_name, messages).encode("utf-8")
    json_path.write_bytes(json_bytes)
    md_path.write_bytes(md_bytes)

    manifest = {
        "schema_version": 1,
        "guild_id": guild_id,
        "channel_id": channel_id,
        "export_scope": export_scope,
        "case_number": case_number,
        "message_count": len(messages),
        "files": {
            json_path.name: hashlib.sha256(json_bytes).hexdigest(),
            md_path.name: hashlib.sha256(md_bytes).hexdigest(),
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    return {"json": json_path, "markdown": md_path, "manifest": manifest_path}


def verify_export(paths: dict[str, Path]) -> bool:
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    for kind in ("json", "markdown"):
        path = paths[kind]
        expected = manifest["files"].get(path.name)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected != actual:
            return False
    return True
