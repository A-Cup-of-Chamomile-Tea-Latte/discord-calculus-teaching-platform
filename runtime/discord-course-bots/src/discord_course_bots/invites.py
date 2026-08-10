from __future__ import annotations

import os
from urllib.parse import urlencode

from dotenv import load_dotenv

# course_assistant: Manage Channels, View Channels, Send Messages, Embed Links,
# Attach Files, Read Message History, Manage Nicknames, Manage Roles,
# Manage Threads, Send Messages in Threads.
COURSE_ASSISTANT_PERMISSIONS = (
    16 | 1024 | 2048 | 16384 | 32768 | 65536 | 134217728 | 268435456 | 17179869184 | 274877906944
)
DUMP_BOT_PERMISSIONS = 1024 | 65536


def _url(client_id: str, permissions: int, commands: bool) -> str:
    scopes = "bot applications.commands" if commands else "bot"
    return "https://discord.com/oauth2/authorize?" + urlencode(
        {
            "client_id": client_id,
            "permissions": str(permissions),
            "scope": scopes,
        }
    )


def main() -> None:
    load_dotenv()
    course_id = os.getenv("COURSE_ASSISTANT_CLIENT_ID", "").strip()
    dump_id = os.getenv("DUMP_BOT_CLIENT_ID", "").strip()
    missing = [
        name
        for name, value in (
            ("COURSE_ASSISTANT_CLIENT_ID", course_id),
            ("DUMP_BOT_CLIENT_ID", dump_id),
        )
        if not value
    ]
    if missing:
        raise SystemExit("Missing in .env: " + ", ".join(missing))
    print("course_assistant invite:\n" + _url(course_id, COURSE_ASSISTANT_PERMISSIONS, True))
    print("\ndump_bot invite:\n" + _url(dump_id, DUMP_BOT_PERMISSIONS, False))


if __name__ == "__main__":
    main()
