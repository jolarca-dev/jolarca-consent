"""Smoke tests for repository scaffold."""

from pathlib import Path


def test_required_files_exist() -> None:
    """Verify that all required governance files exist."""
    repo_root = Path(__file__).parent.parent

    required_files = [
        "AGENTS.md",
        "README.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "SECURITY.md",
        "Makefile",
        "pyproject.toml",
        ".editorconfig",
        ".gitignore",
        ".pre-commit-config.yaml",
        "docs/architecture.md",
        "docs/threat-model.md",
        "docs/migration-plan.md",
        "docs/adr/README.md",
    ]

    for file_path in required_files:
        full_path = repo_root / file_path
        assert full_path.is_file(), f"Required file missing: {file_path}"


def test_main_py_runs() -> None:
    """Verify that main.py smoke-check passes."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"main.py failed: {result.stderr}"
