from __future__ import annotations

import copy
from pathlib import Path

from tools.config_proposal import generate_documents, load_bundle, validate_bundle
from tools.config_proposal.core import ConfigBundle

ROOT = Path(__file__).resolve().parents[2]


def test_proposed_configuration_passes_schema_and_custom_validation() -> None:
    bundle = load_bundle(ROOT)
    issues = validate_bundle(ROOT, bundle)
    assert [issue for issue in issues if issue.severity == "ERROR"] == []
    assert all(issue.code != "LEGACY_STATUS_DRIFT" for issue in issues)


def test_rejects_private_support_visibility_leak() -> None:
    bundle = load_bundle(ROOT)
    server = copy.deepcopy(bundle.server)
    private_channel = next(
        item for item in server["channels"] if item["key"] == "private_case_template"
    )
    private_channel["permissions"]["student"]["allow"].append("VIEW")
    modified = ConfigBundle(server, bundle.portal, bundle.workflow, bundle.data_policy)
    issues = validate_bundle(ROOT, modified)
    assert any(issue.code == "PRIVATE_SUPPORT_LEAK" for issue in issues)


def test_rejects_administrator_and_broad_dump_bot_scope() -> None:
    bundle = load_bundle(ROOT)
    server = copy.deepcopy(bundle.server)
    dump_bot = next(item for item in server["botPermissions"] if item["key"] == "dump_bot")
    dump_bot["permissions"].append("ADMINISTRATOR")
    dump_bot["scopedAreas"].append("community")
    modified = ConfigBundle(server, bundle.portal, bundle.workflow, bundle.data_policy)
    codes = {issue.code for issue in validate_bundle(ROOT, modified)}
    assert "ADMINISTRATOR_FORBIDDEN" in codes
    assert "BOT_PERMISSION_NOT_ALLOWLISTED" in codes
    assert "DUMP_BOT_SCOPE_TOO_BROAD" in codes


def test_rejects_dump_bot_public_write_and_missing_archive_access() -> None:
    bundle = load_bundle(ROOT)
    server = copy.deepcopy(bundle.server)
    public_forum = next(item for item in server["channels"] if item["key"] == "math_questions")
    public_forum["permissions"]["dump_bot"]["allow"] = ["POST"]
    modified = ConfigBundle(server, bundle.portal, bundle.workflow, bundle.data_policy)
    codes = {issue.code for issue in validate_bundle(ROOT, modified)}
    assert "DUMP_BOT_READ_SCOPE_MISSING" in codes
    assert "DUMP_BOT_PUBLIC_WRITE_FORBIDDEN" in codes


def test_generated_documents_are_deterministic_and_config_derived(tmp_path: Path) -> None:
    bundle = load_bundle(ROOT)
    issues = validate_bundle(ROOT, bundle)
    first_paths = generate_documents(tmp_path, bundle, issues)
    first = {path.relative_to(tmp_path): path.read_text(encoding="utf-8") for path in first_paths}
    second_paths = generate_documents(tmp_path, bundle, issues)
    second = {path.relative_to(tmp_path): path.read_text(encoding="utf-8") for path in second_paths}
    assert first == second
    assert "Math Questions" in first[Path("docs/generated/channel-tree.md")]
    assert "AUTO_CLOSED" in first[Path("docs/generated/case-lifecycle.md")]


def test_latest_case_lifecycle_and_ai_choices_are_explicit() -> None:
    bundle = load_bundle(ROOT)
    states = {item["key"] for item in bundle.workflow["states"]}
    transitions = {
        (item["from"], item["to"], item["event"]) for item in bundle.workflow["transitions"]
    }
    assert states == {"OPEN", "TRACKED", "IDLE", "CLOSED", "AUTO_CLOSED"}
    assert ("TRACKED", "IDLE", "FIRST_48H_WITHOUT_LEARNER_REPLY") in transitions
    assert ("IDLE", "AUTO_CLOSED", "SECOND_48H_WITHOUT_LEARNER_REPLY") in transitions
    assert bundle.workflow["aiPermission"] == {
        "required": True,
        "preselected": False,
        "values": ["YES", "NO"],
        "originalPosterNoExcludesCase": True,
        "otherAuthorFilteringRequired": True,
    }
