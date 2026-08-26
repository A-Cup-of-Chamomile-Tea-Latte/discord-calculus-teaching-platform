import json
from pathlib import Path

from bots.common.toolchain_smoke import runtime_mode
from tools.quality.check_secrets import candidate_files, scan_file, scan_repository


def test_root_npm_scripts_use_the_portable_python_launcher() -> None:
    root = Path(__file__).resolve().parents[1]
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    python_scripts = ("format", "format:check", "lint", "typecheck", "test:py", "secrets")

    assert (root / "tools/run-python.mjs").is_file()
    for name in python_scripts:
        command = package["scripts"][name]
        assert "node tools/run-python.mjs" in command
        assert " python -m " not in f" {command} "


def test_portable_python_launcher_sets_repository_import_paths() -> None:
    root = Path(__file__).resolve().parents[1]
    launcher = (root / "tools/run-python.mjs").read_text(encoding="utf-8")
    assert 'join(repositoryRoot, "runtime", "discord-course-bots", "src")' in launcher
    assert "PYTHONPATH" in launcher


def test_python_baseline_uses_fixture_mode() -> None:
    assert runtime_mode() == "fixture-only"


def test_secret_scanner_rejects_assigned_token(tmp_path: Path) -> None:
    sample = tmp_path / "unsafe.env"
    sample.write_text("DISCORD_BOT_TOKEN=abcdefghijklmnopqrstuvwxyz\n", encoding="utf-8")
    assert [finding.rule for finding in scan_file(sample)] == ["assigned-secret"]


def test_repository_candidates_have_no_obvious_secrets() -> None:
    root = Path(__file__).resolve().parents[1]
    assert scan_repository(root) == []


def test_secret_scanner_falls_back_safely_without_git_metadata(tmp_path: Path) -> None:
    (tmp_path / "safe.py").write_text("MODE = 'fixture'\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("DISCORD_BOT_TOKEN=\n", encoding="utf-8")
    excluded_files = (
        tmp_path / ".env",
        tmp_path / "node_modules" / "unsafe.js",
        tmp_path / "dist" / "unsafe.js",
        tmp_path / ".venv" / "unsafe.py",
        tmp_path / ".pytest_cache" / "unsafe.txt",
        tmp_path / "exports" / "unsafe.json",
    )
    for path in excluded_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("DISCORD_BOT_TOKEN=abcdefghijklmnopqrstuvwxyz\n", encoding="utf-8")
    (tmp_path / "handoff.zip").write_bytes(b"not-a-real-archive")
    (tmp_path / ".DS_Store").write_bytes(b"mac metadata")

    candidates = {path.relative_to(tmp_path).as_posix() for path in candidate_files(tmp_path)}

    assert candidates == {".env.example", "safe.py"}
    assert scan_repository(tmp_path) == []
