from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
FIXTURE_ROOTS = (
    ROOT / "fixtures",
    ROOT / "apps" / "gas" / "fixtures",
    ROOT / "contracts" / "examples",
)

INSTITUTIONAL_DOMAIN = re.compile(r"\b(?:[A-Za-z0-9-]+\.)*ntu\.edu\.tw\b", re.IGNORECASE)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+)")
TAIWAN_PHONE = re.compile(r"(?<!\d)(?:09\d{8}|\+886[ -]?9\d{8}|\d{3}[- ]\d{3}[- ]\d{4})(?!\d)")
SECRET_SHAPE = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9]{36,}|AIza[0-9A-Za-z_-]{30,}|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)


def fixture_files() -> list[Path]:
    return sorted(path for root in FIXTURE_ROOTS for path in root.rglob("*") if path.is_file())


def test_all_fixture_files_are_utf8_and_json_files_parse() -> None:
    files = fixture_files()
    assert files
    for path in files:
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            json.loads(text)


def test_all_fixture_trees_reject_real_data_and_secret_shapes() -> None:
    for path in fixture_files():
        text = path.read_text(encoding="utf-8")
        assert INSTITUTIONAL_DOMAIN.search(text) is None, path
        assert TAIWAN_PHONE.search(text) is None, path
        assert SECRET_SHAPE.search(text) is None, path
        assert set(EMAIL.findall(text)) <= {"example.com"}, path


def test_ci_is_read_only_secretless_and_non_deploying() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    required_jobs = {
        "code-quality",
        "contracts-and-fixtures",
        "python-tests",
        "generated-exports",
        "portal",
        "gas",
    }
    for job in required_jobs:
        assert re.search(rf"^  {re.escape(job)}:\s*$", workflow, re.MULTILINE), job
    assert "permissions:\n  contents: read" in workflow
    assert "${{ secrets." not in workflow
    assert "actions/deploy" not in workflow
    assert "environment:" not in workflow
    assert "pages: write" not in workflow
    assert "id-token: write" not in workflow
    assert "npm ci" in workflow
    assert 'python -m pip install --disable-pip-version-check -e ".[dev]"' in workflow


def test_ci_has_dependency_caches_and_no_external_application_commands() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count("cache: npm") == 3
    assert workflow.count("cache: pip") == 4
    forbidden_commands = ("curl ", "wget ", "clasp ", "gh ", "discord.com/api")
    assert all(command not in workflow for command in forbidden_commands)
