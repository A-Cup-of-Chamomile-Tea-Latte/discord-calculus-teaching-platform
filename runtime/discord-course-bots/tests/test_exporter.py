import json
from pathlib import Path

from discord_course_bots.dump_bot.exporter import ExportedMessage, verify_export, write_export


def test_write_export_and_manifest(tmp_path: Path) -> None:
    message = ExportedMessage(
        id=1,
        author_id=2,
        author_display="tester",
        created_at="2026-07-29T00:00:00+00:00",
        edited_at=None,
        content="hello",
        reference_message_id=None,
        attachments=[],
    )
    paths = write_export(
        output_dir=tmp_path,
        guild_id=10,
        channel_id=20,
        channel_name="thread",
        messages=[message],
        export_scope="public",
        case_number="C01-ABC234-0729-1015",
    )
    assert all(path.exists() for path in paths.values())
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert manifest["message_count"] == 1
    assert manifest["export_scope"] == "public"
    assert manifest["case_number"] == "C01-ABC234-0729-1015"
    assert set(manifest["files"]) == {paths["json"].name, paths["markdown"].name}
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert payload["export_scope"] == "public"
    assert payload["case_number"] == "C01-ABC234-0729-1015"
    assert verify_export(paths) is True
    paths["json"].write_text("tampered", encoding="utf-8")
    assert verify_export(paths) is False
