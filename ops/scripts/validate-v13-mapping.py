#!/usr/bin/env python3
"""Validate the shape of the v13 deployment mapping without printing IDs."""

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
    "forum.other_questions",
}
EXPECTED_FORUM_SOURCES = {
    "forum.math_questions": "math_questions",
    "forum.coursework_systems": "coursework_systems",
    "forum.other_questions": "other_problem_free_talk",
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
    resource_ids: list[tuple[str, str]] = []
    try:
        value = load(args.mapping)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(json.dumps({"status": "INVALID", "errors": [str(error)]}, ensure_ascii=False))
        return 2

    if value.get("schemaVersion") != "1.0":
        errors.append("schemaVersion")
    if value.get("termCode") != "115-1":
        errors.append("termCode")

    def required_id(path: str, candidate: object, *, resource: bool = True) -> None:
        if candidate is None:
            missing.append(path)
        elif not SNOWFLAKE.fullmatch(str(candidate)):
            errors.append(path)
        elif resource:
            resource_ids.append((path, str(candidate)))

    server = value.get("server")
    if not isinstance(server, dict):
        errors.append("server")
    else:
        required_id("server.guildId", server.get("guildId"), resource=False)
        for key in ("courseRole", "visitorRole"):
            role = server.get(key)
            if not isinstance(role, dict):
                errors.append(f"server.{key}")
            else:
                required_id(f"server.{key}.discordId", role.get("discordId"))
        course_role = server.get("courseRole")
        if isinstance(course_role, dict):
            if course_role.get("selectedLogicalKey") != "verified_member":
                errors.append("server.courseRole.selectedLogicalKey")
            if course_role.get("proposedSourceKeys") != ["verified_member"]:
                errors.append("server.courseRole.proposedSourceKeys")
        visitor_role = server.get("visitorRole")
        if isinstance(visitor_role, dict) and visitor_role.get("proposedSourceKey") != "guest":
            errors.append("server.visitorRole.proposedSourceKey")

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
            elif item.get("sourceKey") != EXPECTED_FORUM_SOURCES[key]:
                errors.append(f"forums.{key}.sourceKey")
            required_id(f"forums.{key}.discordId", item.get("discordId"))
    if actual_forums != EXPECTED_FORUM_KEYS:
        errors.append("forums.coverage")

    category = value.get("privateSupportCategory")
    if not isinstance(category, dict):
        errors.append("privateSupportCategory")
    else:
        if category.get("logicalKey") != "category.private_support":
            errors.append("privateSupportCategory.logicalKey")
        if category.get("sourceKey") != "private_support":
            errors.append("privateSupportCategory.sourceKey")
        required_id("privateSupportCategory.discordId", category.get("discordId"))

    reviewer = value.get("reviewerMapping")
    if not isinstance(reviewer, dict):
        errors.append("reviewerMapping")
    else:
        if reviewer.get("authorizationMode") != "EXPLICIT_RUNTIME_USER_GRANT":
            errors.append("reviewerMapping.authorizationMode")
        if reviewer.get("reviewerLevel") != "REVIEWER":
            errors.append("reviewerMapping.reviewerLevel")
        if reviewer.get("systemAdminLevel") != "SYSTEM_ADMIN":
            errors.append("reviewerMapping.systemAdminLevel")
        if not (
            reviewer.get("bootstrapOwnerConfiguredInSecureRuntime") is True
            or reviewer.get("grantsConfiguredInSecureRuntime") is True
        ):
            missing.append("reviewerMapping.secureRuntimeBootstrapOrGrants")

    seen_ids: dict[str, str] = {}
    for path, resource_id in resource_ids:
        previous = seen_ids.get(resource_id)
        if previous is not None:
            errors.extend((previous, path, "resourceIds.duplicate"))
        else:
            seen_ids[resource_id] = path

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
        "inventoryGuildMembership": "NOT_CHECKED",
        "sensitiveValuesPrinted": False,
    }
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    if errors or (missing and not args.allow_pending):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
