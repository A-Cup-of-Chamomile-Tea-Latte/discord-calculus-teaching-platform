from discord_course_bots.dump_bot.cli import build_parser


def test_public_export_command_uses_a_thread_id_and_public_directory() -> None:
    args = build_parser().parse_args(["export-public", "--thread-id", "123"])
    assert args.command == "export-public"
    assert args.thread_id == 123
    assert str(args.output_dir) == "exports/public"


def test_private_export_command_uses_a_channel_id_and_private_directory() -> None:
    args = build_parser().parse_args(["export-private", "--channel-id", "456"])
    assert args.command == "export-private"
    assert args.channel_id == 456
    assert str(args.output_dir) == "exports/private"
