from __future__ import annotations

from pathlib import Path

import pytest

from bots.common.contracts import ContractRegistry
from bots.common.errors import ContractValidationError

ROOT = Path(__file__).resolve().parents[2]


def test_project_contract_registry_loads_and_validates_fixture_records() -> None:
    registry = ContractRegistry.project_default()
    records = registry.load_records(
        "verified-email.schema.json",
        ROOT / "fixtures" / "users" / "verified-emails.json",
    )
    assert len(records) == 5
    assert "case.schema.json" in registry.schema_names


def test_contract_registry_accepts_valid_and_rejects_invalid_examples() -> None:
    registry = ContractRegistry.project_default()
    registry.load_and_validate(
        "activation-code.schema.json",
        ROOT / "contracts" / "examples" / "valid" / "activation-code.json",
    )
    with pytest.raises(ContractValidationError, match="additionalProperties") as error:
        registry.load_and_validate(
            "activation-code.schema.json",
            ROOT / "contracts" / "examples" / "invalid" / "activation-code-with-plaintext.json",
        )
    assert "FICTIONAL-PLAINTEXT-NONCE" not in str(error.value)


def test_unknown_or_unsafe_schema_names_fail_without_file_traversal() -> None:
    registry = ContractRegistry.project_default()
    with pytest.raises(ContractValidationError, match="schema name is invalid"):
        registry.validate("../case.schema.json", {})
    with pytest.raises(ContractValidationError, match="Unknown contract schema"):
        registry.validate("missing.schema.json", {})
