from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "contracts" / "schemas"
EXAMPLE_DIR = ROOT / "contracts" / "examples"


def load_json(path: Path) -> dict[str, Any]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


SCHEMAS = {path.name: load_json(path) for path in sorted(SCHEMA_DIR.glob("*.schema.json"))}
REGISTRY = Registry().with_resources(
    (str(schema["$id"]), Resource.from_contents(schema)) for schema in SCHEMAS.values()
)
MANIFEST = load_json(EXAMPLE_DIR / "manifest.json")


def validator(schema_name: str) -> Draft202012Validator:
    return Draft202012Validator(
        SCHEMAS[schema_name], registry=REGISTRY, format_checker=FormatChecker()
    )


def entries(kind: str) -> Iterator[dict[str, str]]:
    raw_entries = MANIFEST[kind]
    assert isinstance(raw_entries, list)
    for entry in raw_entries:
        assert isinstance(entry, dict)
        yield {str(key): str(value) for key, value in entry.items()}


@pytest.mark.parametrize("entry", list(entries("valid")), ids=lambda item: item["instance"])
def test_valid_examples(entry: dict[str, str]) -> None:
    instance = load_json(EXAMPLE_DIR / entry["instance"])
    errors = sorted(
        validator(entry["schema"]).iter_errors(instance), key=lambda error: list(error.path)
    )
    assert errors == []


@pytest.mark.parametrize("entry", list(entries("invalid")), ids=lambda item: item["instance"])
def test_invalid_examples_fail_for_documented_reason(entry: dict[str, str]) -> None:
    instance = load_json(EXAMPLE_DIR / entry["instance"])
    errors = list(validator(entry["schema"]).iter_errors(instance))
    assert entry["reason"].strip()
    assert errors, entry["reason"]


def test_all_schemas_are_valid_draft_2020_12() -> None:
    expected_fixture_first_models = {
        "active-case.schema.json",
        "archive-index.schema.json",
        "changed-case-queue.schema.json",
        "command-queue.schema.json",
        "email-queue.schema.json",
        "discord-structure-inventory.schema.json",
        "sanitized-package.schema.json",
        "sync-state.schema.json",
        "weekly-maintenance-run.schema.json",
    }
    assert expected_fixture_first_models <= SCHEMAS.keys()
    for schema in SCHEMAS.values():
        Draft202012Validator.check_schema(schema)


def test_fixed_case_status_vocabulary() -> None:
    common = SCHEMAS["common.schema.json"]
    assert common["$defs"]["caseStatus"]["enum"] == [
        "OPEN",
        "WAITING_FOR_STUDENT",
        "ANSWERED",
        "ESCALATED",
        "CLOSED",
    ]


def test_ids_are_separate_from_display_labels() -> None:
    user_properties = SCHEMAS["user.schema.json"]["properties"]
    case_properties = SCHEMAS["case.schema.json"]["properties"]
    assert {"userId", "displayLabel"} <= user_properties.keys()
    assert {"caseId", "caseNumber"} <= case_properties.keys()


def property_names(value: object) -> Iterator[str]:
    if isinstance(value, dict):
        properties = value.get("properties")
        if isinstance(properties, dict):
            yield from (str(name) for name in properties)
        for child in value.values():
            yield from property_names(child)
    elif isinstance(value, list):
        for child in value:
            yield from property_names(child)


def test_contracts_define_no_raw_secret_fields() -> None:
    forbidden = re.compile(
        r"^(?:accessToken|refreshToken|oauthToken|botToken|plaintextCode|rawSecret|privateKey)$",
        re.IGNORECASE,
    )
    names = {name for schema in SCHEMAS.values() for name in property_names(schema)}
    assert not {name for name in names if forbidden.match(name)}
