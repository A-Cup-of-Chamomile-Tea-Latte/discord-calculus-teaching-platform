from __future__ import annotations

import argparse
import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

from discord_course_bots.apps_script_transport import APPS_SCRIPT_SCOPE


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Create a revocable authorized-user credential for the GAS bridge"
    )
    result.add_argument("--client-secrets", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--no-browser", action="store_true")
    return result


def main() -> None:
    args = parser().parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite an existing OAuth credential")
    flow = InstalledAppFlow.from_client_secrets_file(str(args.client_secrets), [APPS_SCRIPT_SCOPE])
    credentials = flow.run_local_server(
        host="127.0.0.1",
        port=0,
        open_browser=not args.no_browser,
        authorization_prompt_message="Open this URL in the Ding Ding Chrome profile:\n{url}",
        success_message="Bridge OAuth completed. You may close this page.",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(credentials.to_json(), encoding="utf-8")
    os.chmod(args.output, 0o600)
    print(f"OAuth credential created with mode 0600: {args.output}")


if __name__ == "__main__":
    main()
