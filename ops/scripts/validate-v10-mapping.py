#!/usr/bin/env python3
"""Validate the shape of the v10 production mapping without printing IDs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

EXPECTED_MODULES = {
    **{f"{code:02d}": "M1" for code in range(1, 5)},
    **{f"{code:02d}": "M2" for code in range(5, 10)},
    **{f"{code:02d}": "M3" for code in range(10, 14)},
    **{f"{code:02d}": "M4" for code in range(14, 17)},
}
EXPECTED_FORUM_KEYS = {
    "forum.math_questions",
    "forum.coursework_systems",
    "forum.other_problem_free_talk",
}
SNOWFLAKE = re.compile(r"^[0-9]{17,20}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mapping", type=Path)
    parser.add_argument(
        "--allow-pending",
        action="store_true",
        help="Report shape/missing values without failing on owner-provided values.",
    )
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("mapping must be a JSON object")
    return value


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    missing: list[str] = []
    try:
        value = load(args.mapping)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(json.dumps({"status": "INVALID", "errors": [str(error)]}, ensure_ascii=False))
        return 2

    if value.get("schemaVersion") != "1.0":
        errors.append("schemaVersion")
    if value.get("termCode") != "115-1":
        errors.append("termCode")

    def required_id(path: str, candidate: object) -> None:
        if candidate is None:
            missing.append(path)
        elif not SNOWFLAKE.fullmatch(str(candidate)):
            errors.append(path)

    server = value.get("server")
    if not isinstance(server, dict):
        errors.append("server")
    else:
        required_id("server.guildId", server.get("guildId"))
        for key in ("courseRole", "visitorRole"):
            role = server.get(key)
            if not isinstance(role, dict):
                errors.append(f"server.{key}")
            else:
                required_id(f"server.{key}.discordId", role.get("discordId"))
        course_role = server.get("courseRole")
        if isinstance(course_role, dict) and not course_role.get("selectedLogicalKey"):
            missing.append("server.courseRole.selectedLogicalKey")

    classes = value.get("classRoles")
    expected_classes = set(EXPECTED_MODULES)
    actual_classes = set()
    class_items: list[object] = []
    if not isinstance(classes, list):
        errors.append("classRoles")
    else:
        class_items = classes
        for item in classes:
            if not isinstance(item, dict):
                errors.append("classRoles.item")
                continue
            code = str(item.get("classCode", ""))
            actual_classes.add(code)
            if code not in EXPECTED_MODULES or item.get("moduleCode") != EXPECTED_MODULES.get(code):
                errors.append(f"classRoles.{code}.moduleCode")
            if item.get("logicalKey") != f"class.C{code}":
                errors.append(f"classRoles.{code}.logicalKey")
            required_id(f"classRoles.{code}.discordId", item.get("discordId"))
    if actual_classes != expected_classes:
        errors.append("classRoles.coverage")

    forums = value.get("forums")
    actual_forums = set()
    if not isinstance(forums, list):
        errors.append("forums")
    else:
        for item in forums:
            if not isinstance(item, dict):
                errors.append("forums.item")
                continue
            key = str(item.get("logicalKey", ""))
            actual_forums.add(key)
            if key not in EXPECTED_FORUM_KEYS:
                errors.append(f"forums.{key}.logicalKey")
            required_id(f"forums.{key}.discordId", item.get("discordId"))
    if actual_forums != EXPECTED_FORUM_KEYS:
        errors.append("forums.coverage")

    category = value.get("privateSupportCategory")
    if not isinstance(category, dict):
        errors.append("privateSupportCategory")
    else:
        required_id("privateSupportCategory.discordId", category.get("discordId"))

    reviewer = value.get("reviewerMapping")
    if not isinstance(reviewer, dict):
        errors.append("reviewerMapping")
    elif reviewer.get("grantsConfiguredInSecureRuntime") is not True:
        missing.append("reviewerMapping.secureRuntimeGrants")

    errors = sorted(set(errors))
    missing = sorted(set(missing))
    status = "PASS" if not errors and not missing else "PENDING_OWNER_INPUT"
    if errors:
        status = "INVALID"
    receipt = {
        "status": status,
        "shapeValid": not errors,
        "missingCount": len(missing),
        "missingFields": missing,
        "errorCount": len(errors),
        "errorFields": errors,
        "classModuleMapping": "PASS"
        if actual_classes == expected_classes
        and not any(
            item.get("moduleCode") != EXPECTED_MODULES.get(str(item.get("classCode", "")))
            for item in class_items
            if isinstance(item, dict)
        )
        else "FAIL",
        "sensitiveValuesReadOrPrinted": False,
    }
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    if errors or (missing and not args.allow_pending):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
