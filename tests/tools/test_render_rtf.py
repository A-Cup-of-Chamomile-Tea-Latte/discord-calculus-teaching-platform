from __future__ import annotations

from tools.reporting.render_rtf import render_markdown_to_rtf


def test_rtf_is_derived_from_markdown_and_escapes_unicode() -> None:
    rendered = render_markdown_to_rtf("# 標題\n\n- 完成 `fixture`\n")
    assert rendered.startswith(r"{\rtf1")
    assert r"\u27161?" in rendered
    assert r"\bullet\tab" in rendered
    assert "fixture" in rendered
    assert "`" not in rendered


def test_rtf_escapes_control_characters_and_links() -> None:
    rendered = render_markdown_to_rtf(r"[guide](docs/a.md) and {safe}\path")
    assert "guide (docs/a.md)" in rendered
    assert r"\{safe\}\\path" in rendered
