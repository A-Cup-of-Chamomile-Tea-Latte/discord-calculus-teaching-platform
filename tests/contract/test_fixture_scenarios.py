from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = ROOT / "fixtures"
SCHEMA_DIR = ROOT / "contracts" / "schemas"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_records(relative_path: str) -> list[dict[str, Any]]:
    value = load_json(FIXTURE_DIR / relative_path)
    assert isinstance(value, list)
    assert all(isinstance(item, dict) for item in value)
    return value


SCHEMAS = {path.name: load_json(path) for path in sorted(SCHEMA_DIR.glob("*.schema.json"))}
REGISTRY = Registry().with_resources(
    (str(schema["$id"]), Resource.from_contents(schema)) for schema in SCHEMAS.values()
)
MANIFEST: dict[str, Any] = load_json(FIXTURE_DIR / "MANIFEST.json")


def test_all_record_fixtures_validate_against_contracts() -> None:
    record_count = 0
    for record_set in MANIFEST["recordSets"]:
        records = load_records(str(record_set["file"]))
        contract = Draft202012Validator(
            SCHEMAS[str(record_set["schema"])],
            registry=REGISTRY,
            format_checker=FormatChecker(),
        )
        for index, record in enumerate(records):
            errors = list(contract.iter_errors(record))
            assert errors == [], f"{record_set['file']}[{index}]: {errors}"
        record_count += len(records)
    assert record_count == 43


def test_fixture_text_rejects_real_data_and_secret_shapes() -> None:
    institutional_email = re.compile(r"ntu\.edu\.tw", re.IGNORECASE)
    phone = re.compile(r"(?<!\d)(?:09\d{8}|\+886[ -]?9\d{8}|\d{3}[- ]\d{3}[- ]\d{4})(?!\d)")
    obvious_secret = re.compile(
        r"(?:gh[pousr]_[A-Za-z0-9]{36,}|AIza[0-9A-Za-z_-]{30,}|"
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
    )
    for path in FIXTURE_DIR.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            assert not institutional_email.search(text), path
            assert not phone.search(text), path
            assert not obvious_secret.search(text), path


def test_all_fixture_email_addresses_use_example_com() -> None:
    email_pattern = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+)")
    addresses: list[str] = []
    for path in FIXTURE_DIR.rglob("*.json"):
        addresses.extend(email_pattern.findall(path.read_text(encoding="utf-8")))
    assert addresses
    assert set(addresses) == {"example.com"}


def test_users_classes_and_course_aliases_are_consistent() -> None:
    users = load_records("users/users.json")
    memberships = load_records("users/course-memberships.json")
    assert len(users) >= 3
    assert {membership["classCode"] for membership in memberships} == {"01", "02"}
    for membership in memberships:
        assert membership["courseAlias"] == (
            f"{membership['classCode']}{membership['joiningOrder']:03d}"
        )


def test_institutional_and_contact_emails_are_separate_records() -> None:
    emails = load_records("users/verified-emails.json")
    amber = [record for record in emails if record["userId"] == "usr_amber"]
    assert {record["kind"] for record in amber} == {"INSTITUTIONAL", "CONTACT"}
    assert len({record["verifiedEmailId"] for record in amber}) == 2
    assert sum(bool(record["isPrimary"]) for record in amber) == 1


def test_cases_cover_workflow_and_privacy_modes() -> None:
    cases = load_records("cases/cases.json")
    general = [case for case in cases if case["caseType"] == "GENERAL"]
    private = [case for case in cases if case["caseType"] == "PRIVATE_SUPPORT"]
    assert {case["status"] for case in general} == {
        "OPEN",
        "WAITING_FOR_STUDENT",
        "ANSWERED",
        "ESCALATED",
        "CLOSED",
    }
    assert any(case["authorDisplayMode"] == "COURSE_ALIAS" for case in general)
    assert any(case["authorDisplayMode"] == "ANONYMOUS" for case in general)
    assert len(private) == 1
    assert isinstance(private[0]["caseNumber"], str)
    assert private[0]["caseNumber"].endswith("-P")
    assert private[0]["visibility"] == "TEACHING_STAFF"
    assert private[0]["analysisPermission"] == "EXCLUDED"


def test_message_thread_has_replies_edits_attachments_and_mixed_consent() -> None:
    messages = load_records("messages/case-000421-thread.json")
    message_ids = {message["messageId"] for message in messages}
    assert all(message["caseId"] == "case_000421" for message in messages)
    assert any(message["parentMessageId"] in message_ids for message in messages)
    assert any(message["editedAt"] is not None for message in messages)
    assert any(message["attachments"] for message in messages)
    assert {message["analysisPermission"] for message in messages} == {
        "INHERIT",
        "INCLUDED",
        "EXCLUDED",
    }


def test_activation_code_and_export_states_are_complete() -> None:
    activation_codes = load_records("users/activation-codes.json")
    exports = load_records("exports/export-manifests.json")
    assert {code["status"] for code in activation_codes} == {
        "UNUSED",
        "USED",
        "EXPIRED",
        "REVOKED",
    }
    private_exports = [item for item in exports if item["caseType"] == "PRIVATE_SUPPORT"]
    assert private_exports
    assert all(item["analysisPermission"] == "EXCLUDED" for item in private_exports)


def test_record_links_and_parents_resolve() -> None:
    user_records = load_records("users/users.json")
    users = {item["userId"] for item in user_records}
    verified_emails = {
        item["verifiedEmailId"]: item for item in load_records("users/verified-emails.json")
    }
    cases = {item["caseId"]: item for item in load_records("cases/cases.json")}
    messages = load_records("messages/case-000421-thread.json")
    message_ids = {item["messageId"] for item in messages}
    assert all(case["createdByUserId"] in users for case in cases.values())
    assert all(
        email_id in verified_emails and verified_emails[email_id]["userId"] == user["userId"]
        for user in user_records
        for email_id in user["verifiedEmailIds"]
    )
    assert all(message["authorUserId"] in users for message in messages)
    assert all(message["caseId"] in cases for message in messages)
    assert all(
        message["parentMessageId"] is None or message["parentMessageId"] in message_ids
        for message in messages
    )


def test_all_five_mock_adapters_are_local_and_consistent() -> None:
    data: dict[str, Any] = load_json(FIXTURE_DIR / "adapters/mock-adapters.json")
    adapters: dict[str, Any] = data["adapters"]
    assert set(adapters) == {
        "caseLookup",
        "discordThreadFetch",
        "sheetsStorage",
        "emailDelivery",
        "activationCodeValidation",
    }
    serialized = json.dumps(data)
    assert "http://" not in serialized and "https://" not in serialized
    for adapter in adapters.values():
        source = adapter.get("sourceFile")
        if source:
            assert (ROOT / str(source)).is_file()
    for worksheet in adapters["sheetsStorage"]["worksheets"]:
        assert (ROOT / str(worksheet["sourceFile"])).is_file()


def test_every_lane_uses_the_same_shared_case() -> None:
    scenario: dict[str, Any] = MANIFEST["sharedScenario"]
    assert scenario["caseId"] == "case_000421"
    assert scenario["caseNumber"] == "C01-7K4M2Q-0702-1000"
    assert set(scenario["consumers"]) == {"portal", "gas", "bots", "tools"}
    case_ids = {case["caseId"] for case in load_records("cases/cases.json")}
    assert scenario["caseId"] in case_ids
