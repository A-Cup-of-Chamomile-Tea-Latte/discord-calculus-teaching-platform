from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "config/academic/115-1/course-operations.yaml"
RECEIPT_PATH = ROOT / "config/academic/115-1/source-receipts.json"
SCHEMA_PATH = ROOT / "config/schema/course-operations.schema.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_1151_course_operations_matches_long_term_schema() -> None:
    spec = _load(SPEC_PATH)
    schema = _load(SCHEMA_PATH)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(spec),
        key=lambda item: list(item.absolute_path),
    )
    assert errors == []


def test_1151_active_sections_and_module_mapping_are_complete() -> None:
    spec = _load(SPEC_PATH)
    sections = spec["sections"]
    assert isinstance(sections, list)
    class_codes = [f"{value:02d}" for value in range(1, 17)]
    expected_modules = ["M1"] * 4 + ["M2"] * 5 + ["M3"] * 4 + ["M4"] * 3
    assert [item["classCode"] for item in sections] == class_codes
    assert [item["sourceLabel"] for item in sections] == [f"模{code}" for code in class_codes]
    assert [item["canonicalClassLabel"] for item in sections] == [
        f"C{code}" for code in class_codes
    ]
    assert [item["moduleCode"] for item in sections] == expected_modules
    assert sum(len(item["practiceSections"]) for item in sections) == 28

    assert spec["modules"] == [
        {"moduleCode": "M1", "displayName": "理工電資", "classCodes": class_codes[0:4]},
        {"moduleCode": "M2", "displayName": "土木機電", "classCodes": class_codes[4:9]},
        {"moduleCode": "M3", "displayName": "經濟商管", "classCodes": class_codes[9:13]},
        {"moduleCode": "M4", "displayName": "農學院", "classCodes": class_codes[13:16]},
    ]
    expected_mapping = [
        {"classCode": code, "moduleCode": module}
        for code, module in zip(class_codes, expected_modules, strict=True)
    ]
    assert spec["classModuleMapping"] == {
        "status": "APPROVED",
        "entries": expected_mapping,
    }

    server = _load(ROOT / "config/proposed/server.yaml")
    workflow = _load(ROOT / "config/proposed/case-workflow.yaml")
    module_codes = ["M1", "M2", "M3", "M4"]
    assert server["modules"] == module_codes
    assert workflow["canonicalTitle"]["modules"] == module_codes
    assert server["classModuleMapping"] == {
        "status": "APPROVED",
        "entries": expected_mapping,
    }


def test_1151_term_identity_and_person_references_are_coherent() -> None:
    spec = _load(SPEC_PATH)
    assert spec["term"] == {
        "termCode": "115-1",
        "calendarSystem": "MINGUO",
        "academicYearRoc": 115,
        "semester": 1,
        "displayName": "115學年度第1學期",
    }
    assert spec["registrationPolicy"] == {
        "classSelectionMode": "USER_SELECTS_DURING_WEB_REGISTRATION",
        "activeClassCodesSource": "SECTIONS",
        "moduleDerivation": "CLASS_MODULE_MAPPING",
        "discordMembershipMode": "BROAD_COURSE_ROLE_PLUS_ALLOWLISTED_CLASS_ROLE",
        "moduleRepresentation": "BACKEND_ATTRIBUTE_ONLY",
        "optionalClassCodeStart": "21",
    }
    assert spec["taCategoryCodes"] == [
        {
            "code": "L",
            "meaning": "TA_LECTURER",
            "discordRoleKeys": ["ta_lecturer"],
        },
        {
            "code": "G",
            "meaning": "TA_GRADER",
            "discordRoleKeys": ["ta_grader"],
        },
        {
            "code": "G_L",
            "meaning": "TA_LECTURER_AND_TA_GRADER",
            "discordRoleKeys": ["ta_lecturer", "ta_grader"],
        },
        {
            "code": "UNSPECIFIED",
            "meaning": "SOURCE_BLANK",
            "discordRoleKeys": [],
        },
    ]

    people = spec["peopleDirectory"]
    instructor_refs = {person["instructorRef"] for person in people["instructors"]}
    ta_refs = {person["taRef"] for person in people["teachingAssistants"]}
    assert len(instructor_refs) == len(people["instructors"])
    assert len(ta_refs) == len(people["teachingAssistants"])

    sections = [*spec["sections"], *spec["referenceOnlySections"]]
    for section in sections:
        assert section["instructorRef"] in instructor_refs
        assignments = {
            assignment["taRef"]: assignment["categoryCode"]
            for assignment in section["taAssignments"]
        }
        assert assignments.keys() <= ta_refs
        for practice in section["practiceSections"]:
            assert practice["taRef"] in assignments
            assert assignments[practice["taRef"]] in {"L", "G_L"}


def test_reference_only_sections_cannot_enter_active_module_mapping() -> None:
    spec = _load(SPEC_PATH)
    active_codes = {entry["classCode"] for entry in spec["classModuleMapping"]["entries"]}
    assert [section["classCode"] for section in spec["referenceOnlySections"]] == ["21"]
    assert [section["canonicalClassLabel"] for section in spec["referenceOnlySections"]] == ["C21"]
    for section in spec["referenceOnlySections"]:
        assert section["classCode"] not in active_codes
        assert section["moduleCode"] is None
        assert section["practiceSections"] == []


def test_tracked_academic_spec_contains_no_direct_personal_directory_fields() -> None:
    spec = _load(SPEC_PATH)
    serialized = json.dumps(spec, ensure_ascii=False)
    forbidden_keys = {"name", "academicId", "phone", "email", "affiliation"}

    def walk(value: object) -> None:
        if isinstance(value, dict):
            assert forbidden_keys.isdisjoint(value)
            for nested in value.values():
                walk(nested)
        elif isinstance(value, list):
            for nested in value:
                walk(nested)

    walk(spec)
    assert not re.search(r"[A-Z][0-9A-Z]{7,8}@|09[0-9]{2}-[0-9]{3}-[0-9]{3}", serialized)


def test_private_source_receipts_match_when_sources_are_present() -> None:
    receipts = _load(RECEIPT_PATH)
    assert receipts["termCode"] == "115-1"
    assert receipts["visibility"] == "PUBLIC_COURSE_OPERATIONS_SOURCE"
    sources = receipts["sources"]
    assert isinstance(sources, list)
    assert len(sources) == 2
    for source in sources:
        path = ROOT / source["path"]
        if not path.exists():
            continue
        assert path.stat().st_mode & 0o777 == 0o644
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
    assert [(source["pages"], source["role"]) for source in sources] == [
        (1, "PRACTICE_GROUPING_AND_CLASSROOMS"),
        (3, "FULL_TA_ROSTER_PUBLIC_COURSE_SOURCE"),
    ]
