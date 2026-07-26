from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from tools.packaging import build_handoff_archive, iter_archive_files

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_EXPORT_FIXTURE = Path("fixtures/exports/export-manifests.json")
REQUIRED_CREDENTIAL_NAMED_TEST_FIXTURE = Path(
    "contracts/examples/invalid/user-with-oauth-token.json"
)


def test_repository_inventory_keeps_export_manifest_fixture() -> None:
    files = iter_archive_files(ROOT)
    assert REQUIRED_EXPORT_FIXTURE in files
    assert REQUIRED_CREDENTIAL_NAMED_TEST_FIXTURE in files
    assert not any(path.parts[0] == "exports" for path in files)
    assert not any("node_modules" in path.parts for path in files)


def test_archive_excludes_operator_exports_without_excluding_fixture_exports(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    (root / "fixtures" / "exports").mkdir(parents=True)
    (root / "fixtures" / "exports" / "export-manifests.json").write_text("[]\n", encoding="utf-8")
    (root / "exports").mkdir()
    (root / "exports" / "real-like-operator-output.json").write_text("{}\n", encoding="utf-8")
    (root / "nested" / "node_modules").mkdir(parents=True)
    (root / "nested" / "node_modules" / "dependency.js").write_text("x", encoding="utf-8")
    (root / "client_secret_fixture.json").write_text("{}\n", encoding="utf-8")
    (root / "README.md").write_text("fixture project\n", encoding="utf-8")
    output = tmp_path / "handoff.zip"

    result = build_handoff_archive(root, output)

    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert archive.testzip() is None
    assert names == ["README.md", "fixtures/exports/export-manifests.json"]
    assert result.file_count == 2


def test_archive_bytes_are_reproducible_when_source_mtime_changes(tmp_path: Path) -> None:
    root = tmp_path / "project"
    fixture = root / "fixtures" / "exports" / "export-manifests.json"
    fixture.parent.mkdir(parents=True)
    fixture.write_text("[]\n", encoding="utf-8")
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    first_result = build_handoff_archive(root, first)
    fixture.touch()
    second_result = build_handoff_archive(root, second)

    assert first.read_bytes() == second.read_bytes()
    assert first_result.sha256 == second_result.sha256


def test_archive_rejects_a_contract_manifest_reference_excluded_from_package(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    export_fixture = root / "fixtures" / "exports" / "export-manifests.json"
    export_fixture.parent.mkdir(parents=True)
    export_fixture.write_text("[]\n", encoding="utf-8")
    examples = root / "contracts" / "examples"
    (examples / "invalid").mkdir(parents=True)
    (examples / "invalid" / "client_secret.json").write_text("{}\n", encoding="utf-8")
    (examples / "manifest.json").write_text(
        '{"valid": [], "invalid": [{"instance": "invalid/client_secret.json"}]}\n',
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="contract examples.*missing"):
        build_handoff_archive(root, tmp_path / "handoff.zip")
