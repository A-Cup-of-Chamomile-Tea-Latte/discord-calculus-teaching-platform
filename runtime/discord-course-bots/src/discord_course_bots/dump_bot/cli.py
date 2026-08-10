from __future__ import annotations

import argparse
from pathlib import Path

from discord_course_bots.logging_config import configure_logging
from discord_course_bots.settings import SettingsError, load_dump_bot_settings
from .client import DumpClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Discord dump bot")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("probe", help="Log in, print visible channels and permissions, then exit")
    sub.add_parser("online", help="Stay online with no write handlers or commands")
    public_export = sub.add_parser("export-public", help="Export one registered public Forum case")
    public_export.add_argument("--thread-id", required=True, type=int)
    public_export.add_argument("--output-dir", type=Path, default=Path("exports/public"))
    private_export = sub.add_parser("export-private", help="Export one registered Private Support case")
    private_export.add_argument("--channel-id", required=True, type=int)
    private_export.add_argument("--output-dir", type=Path, default=Path("exports/private"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        settings = load_dump_bot_settings()
    except SettingsError as exc:
        raise SystemExit(str(exc)) from exc
    configure_logging(settings.log_level)
    client = DumpClient(
        settings,
        mode=args.command,
        channel_id=getattr(args, "thread_id", None) or getattr(args, "channel_id", None),
        output_dir=getattr(args, "output_dir", None),
    )
    client.run(settings.token, log_handler=None)


if __name__ == "__main__":
    main()
