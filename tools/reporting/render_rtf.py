from __future__ import annotations

import argparse
import re
from pathlib import Path

LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _rtf_text(value: str) -> str:
    value = LINK.sub(r"\1 (\2)", value)
    value = value.replace("**", "").replace("__", "").replace("`", "")
    output: list[str] = []
    for character in value:
        if character in "\\{}":
            output.append(f"\\{character}")
            continue
        codepoint = ord(character)
        if 0x20 <= codepoint <= 0x7E:
            output.append(character)
            continue
        encoded = character.encode("utf-16-le")
        for index in range(0, len(encoded), 2):
            unit = int.from_bytes(encoded[index : index + 2], "little")
            signed = unit if unit < 0x8000 else unit - 0x10000
            output.append(f"\\u{signed}?")
    return "".join(output)


def render_markdown_to_rtf(markdown: str) -> str:
    body: list[str] = []
    in_code = False
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            body.append(rf"\pard\li360\f1\fs18 {_rtf_text(line)}\f0\fs22\par")
            continue
        if not line:
            body.append(r"\pard\sa80\par")
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            level = len(heading.group(1))
            size = {1: 36, 2: 30, 3: 26}.get(level, 23)
            body.append(rf"\pard\sb220\sa120\b\fs{size} {_rtf_text(heading.group(2))}\b0\fs22\par")
            continue
        bullet = re.match(r"^\s*[-*]\s+(.+)$", line)
        if bullet:
            body.append(rf"\pard\li360\fi-180\sa70 \bullet\tab {_rtf_text(bullet.group(1))}\par")
            continue
        numbered = re.match(r"^\s*(\d+)\.\s+(.+)$", line)
        if numbered:
            body.append(
                rf"\pard\li360\fi-240\sa70 {numbered.group(1)}.\tab "
                rf"{_rtf_text(numbered.group(2))}\par"
            )
            continue
        body.append(rf"\pard\sa100 {_rtf_text(line)}\par")
    return (
        r"{\rtf1\ansi\deff0"
        r"{\fonttbl{\f0 Helvetica;}{\f1 Menlo;}}"
        r"\viewkind4\uc1\paperw11906\paperh16838\margl1134\margr1134\margt1134\margb1134"
        + "".join(body)
        + "}\n"
    )


def render_file(source: Path, output: Path) -> None:
    markdown = source.read_text(encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown_to_rtf(markdown), encoding="ascii")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Markdown sources to RTF reading copies")
    parser.add_argument("pairs", nargs="+", help="SOURCE.md=OUTPUT.rtf")
    args = parser.parse_args(argv)
    for pair in args.pairs:
        if "=" not in pair:
            parser.error(f"expected SOURCE=OUTPUT, got {pair!r}")
        source_name, output_name = pair.split("=", 1)
        render_file(Path(source_name), Path(output_name))
        print(f"rendered {output_name} from {source_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
