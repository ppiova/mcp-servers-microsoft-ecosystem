#!/usr/bin/env python3
"""Validate the syntax and consistency of the catalog ignore list."""
from __future__ import annotations

import re
import sys
from pathlib import Path

if __package__:
    from .check_servers import extract_repos
else:
    from check_servers import extract_repos

ROOT = Path(__file__).resolve().parents[1]
README_PATH = ROOT / "README.md"
IGNORE_PATH = ROOT / ".discovery-ignore"
REPO_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")


def validate_ignore_list(readme: str, ignore_text: str) -> list[str]:
    """Return consistency errors for `.discovery-ignore`."""
    listed = {f"{owner}/{repo}".lower() for owner, repo in extract_repos(readme)}
    seen: set[str] = set()
    errors: list[str] = []

    for line_number, raw_line in enumerate(ignore_text.splitlines(), start=1):
        entry = raw_line.split("#", 1)[0].strip()
        if not entry:
            continue
        if not REPO_SLUG_RE.fullmatch(entry):
            errors.append(f".discovery-ignore:{line_number}: expected owner/repo, got {entry!r}")
            continue

        normalized = entry.lower()
        if normalized in seen:
            errors.append(f".discovery-ignore:{line_number}: duplicate entry {entry!r}")
        else:
            seen.add(normalized)
        if normalized in listed:
            errors.append(f".discovery-ignore:{line_number}: {entry!r} is already listed in README.md")

    return errors


def main() -> int:
    errors = validate_ignore_list(
        README_PATH.read_text(encoding="utf-8"),
        IGNORE_PATH.read_text(encoding="utf-8"),
    )
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Catalog structure is valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
