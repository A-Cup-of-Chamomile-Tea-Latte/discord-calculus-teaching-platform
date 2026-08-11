from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from discord_course_bots.data_lab.carrier import ensure_staging_carrier, open_staging_repository
from discord_course_bots.data_lab.contracts import canonical_json, utc_z
from discord_course_bots.data_lab.service import (
    apply_ingest,
    case_status,
    dry_run_ingest,
    inspect_run,
    staging_summary,
)
from discord_course_bots.repository_time import utc_now_iso


def _print(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phase 2B synthetic staging data lab")
    parser.add_argument(
        "--lab-root", type=Path, default=Path(".local/phase2b-data-lab")
    )
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest")
    ingest.add_argument("--fixture", required=True)
    mode = ingest.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    ingest.add_argument("--confirm")
    status = commands.add_parser("case-status")
    status.add_argument("--case-ref", required=True)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--run-id", required=True)
    commands.add_parser("summary")
    commands.add_parser("create-case").add_argument("--interactive", action="store_true")
    return parser


def _interactive(root: Path) -> None:
    module = input("Module code (e.g. M01): ").strip().upper()
    keyword = input("Keyword: ").strip()
    lifecycle = input("Initial lifecycle state [OPEN]: ").strip().upper() or "OPEN"
    action = input("TA action [REVIEW/FOLLOW_UP/NONE]: ").strip().upper() or "REVIEW"
    deadline_input = input("Synthetic deadline UTC (blank for none): ").strip()
    if not re.fullmatch(r"[A-Z][A-Z0-9]{0,7}", module):
        raise SystemExit("module must be an uppercase opaque code")
    if not keyword or len(keyword) > 40:
        raise SystemExit("keyword must contain 1–40 characters")
    if lifecycle != "OPEN":
        raise SystemExit("a new synthetic case must start OPEN; close it in a later transition")
    if action not in {"REVIEW", "FOLLOW_UP", "NONE"}:
        raise SystemExit("TA action must be REVIEW, FOLLOW_UP or NONE")
    deadline = None if not deadline_input else utc_z(deadline_input)
    now = utc_now_iso()
    safe_fields = {
        "module": module,
        "keyword": keyword,
        "lifecycleStatus": lifecycle,
        "taAction": action,
        "deadline": deadline,
        "occurredAt": now,
    }
    digest = hashlib.sha256(canonical_json(safe_fields).encode("utf-8")).hexdigest()
    fixture = {
        **safe_fields,
        "caseRef": f"TST-WIZARD-{digest[:10].upper()}",
        "reopenCount": 0,
        "actorRef": "SYN-LAB-TA",
        "analysisEligible": False,
        "fixtureRef": "fixture://interactive/local-only",
    }
    plan = {
        "operation": "CREATE_INTERACTIVE_SYNTHETIC_CASE",
        "environment": "STAGING",
        "syntheticOnly": True,
        "liveDiscordEnabled": False,
        "caseRef": fixture["caseRef"],
        "module": module,
        "keyword": keyword,
        "newStatus": lifecycle,
        "taAction": action,
        "deadline": deadline,
        "outboxScopes": ["CASEBOARD", "HISTORY", "OVERVIEW", "OPERATIONS"],
    }
    nonce = hashlib.sha256(canonical_json(plan).encode("utf-8")).hexdigest()[:24]
    _print({**plan, "confirmationNonce": nonce, "dryRun": True})
    if input("Type the confirmation nonce to apply: ").strip() != nonce:
        raise SystemExit("confirmation cancelled")
    paths = ensure_staging_carrier(root)
    repository = open_staging_repository(paths)
    try:
        result = repository.apply_fixture(fixture, correlation_id=f"run-{digest[:12]}")
    finally:
        repository.close()
    _print(
        {
            "status": "APPLIED",
            "caseRef": result.case_ref,
            "sourceVersion": result.source_version,
            "outboxCount": result.outbox_count,
            "safeResultCode": "INTERACTIVE_SYNTHETIC_CASE_APPLIED",
        }
    )


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "ingest":
        if args.dry_run:
            _print(dry_run_ingest(args.lab_root, args.fixture))
        else:
            if not args.confirm:
                raise SystemExit("--apply requires --confirm <nonce>")
            _print(apply_ingest(args.lab_root, args.fixture, args.confirm))
    elif args.command == "case-status":
        _print(case_status(args.lab_root, args.case_ref))
    elif args.command == "inspect":
        _print(inspect_run(args.lab_root, args.run_id))
    elif args.command == "summary":
        _print(staging_summary(args.lab_root))
    else:
        if not args.interactive:
            raise SystemExit("create-case requires --interactive")
        _interactive(args.lab_root)


if __name__ == "__main__":
    main()
