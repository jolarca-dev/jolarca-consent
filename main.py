#!/usr/bin/env python3
"""Smoke-check of repository tooling.

Verifies that the key governance files exist and are valid. This is the
house convention from jolarca-compliance (README.md:73).

Usage:
    python main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent

REQUIRED_FILES = [
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
    "LICENSE",
    ".github/CODEOWNERS",
    "docs/architecture.md",
    "docs/threat-model.md",
    "docs/migration-plan.md",
    "docs/adr/README.md",
    "docs/adr/ADR-0001-consent-registry-of-record.md",
    "docs/adr/ADR-0002-sha256-append-only-chain.md",
    "docs/adr/ADR-0003-withdrawal-anonymize-dont-delete.md",
]


def check_files() -> int:
    """Check that all required files exist."""
    missing = []
    for file_path in REQUIRED_FILES:
        full_path = REPO / file_path
        if not full_path.is_file():
            missing.append(file_path)

    if missing:
        print(f"ERROR: {len(missing)} required file(s) missing:")
        for f in missing:
            print(f"  - {f}")
        return 1

    print(f"OK: all {len(REQUIRED_FILES)} required files present")
    return 0


def main() -> int:
    """Run all smoke checks."""
    print("jolarca-consent — repository tooling smoke-check")
    print("=" * 60)

    exit_code = 0

    # Check required files
    exit_code |= check_files()

    print("=" * 60)
    if exit_code == 0:
        print("All smoke checks passed")
    else:
        print("Some smoke checks failed")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
