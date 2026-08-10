from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_review_launcher_is_fixture_only_and_stops_both_astro_servers() -> None:
    source = (ROOT / "tools/review/start-review.mjs").read_text(encoding="utf-8")
    assert "127.0.0.1" in source
    assert "C01-7K4M2Q-0702-1000" in source
    assert source.count('"stop"') >= 1
    assert "--background" in source
    assert "discord.com/api" not in source
    assert "googleapis.com" not in source
    assert "fetch(" not in source
    assert "token" not in source.lower().replace("no discord connection, deployment, token", "")
