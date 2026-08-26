from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = PROJECT_ROOT / "config/release/v13-production-mapping.template.json"
VALIDATOR = PROJECT_ROOT / "ops/scripts/validate-v13-mapping.py"


def complete_mapping(tmp_path: Path) -> Path:
    value = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    next_id = 100_000_000_000_000_001

    def assign(item: dict[str, object], key: str = "discordId") -> None:
        nonlocal next_id
        item[key] = str(next_id)
        next_id += 1

    assign(value["server"], "guildId")
    assign(value["server"]["courseRole"])
    assign(value["server"]["visitorRole"])
    for item in value["classRoles"] + value["forums"]:
        assign(item)
    assign(value["privateSupportCategory"])
    value["reviewerMapping"]["bootstrapOwnerConfiguredInSecureRuntime"] = True
    path = tmp_path / "mapping.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def validate(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, VALIDATOR, path], capture_output=True, text=True, check=False
    )


def test_complete_canonical_mapping_passes_without_printing_ids(tmp_path: Path) -> None:
    completed = validate(complete_mapping(tmp_path))

    receipt = json.loads(completed.stdout)
    assert completed.returncode == 0
    assert receipt["status"] == "PASS"
    assert receipt["sensitiveValuesPrinted"] is False
    assert "100000000000000" not in completed.stdout


def test_duplicate_resource_and_noncanonical_course_role_fail(tmp_path: Path) -> None:
    path = complete_mapping(tmp_path)
    value = json.loads(path.read_text(encoding="utf-8"))
    value["server"]["courseRole"]["selectedLogicalKey"] = "registered_audit"
    value["server"]["visitorRole"]["discordId"] = value["server"]["courseRole"]["discordId"]
    path.write_text(json.dumps(value), encoding="utf-8")

    completed = validate(path)
    receipt = json.loads(completed.stdout)
    assert completed.returncode == 1
    assert receipt["status"] == "INVALID"
    assert "server.courseRole.selectedLogicalKey" in receipt["errorFields"]
    assert "resourceIds.duplicate" in receipt["errorFields"]
