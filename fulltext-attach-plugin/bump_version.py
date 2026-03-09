#!/usr/bin/env python3
from __future__ import annotations

"""Bump the add-on release version under the repo's minor-only policy."""

import re
import sys
from pathlib import Path


VERSION_PATH = Path(__file__).resolve().parent / "version.py"
VERSION_PATTERN = re.compile(r'^VERSION = "(\d+)\.(\d+)"$', re.MULTILINE)


def bump_version(bump_type: str = "minor") -> str:
    if bump_type == "patch":
        raise ValueError(
            "Patch bumps are not allowed in this repo. Use 'minor' for normal plugin changes."
        )
    if bump_type not in {"major", "minor"}:
        raise ValueError(f"Unknown bump type: {bump_type}")

    source = VERSION_PATH.read_text()
    match = VERSION_PATTERN.search(source)
    if match is None:
        raise ValueError('Could not parse VERSION = "X.Y" from version.py')

    major = int(match.group(1))
    minor = int(match.group(2))
    old_version = f"{major}.{minor}"

    if bump_type == "major":
        major += 1
        minor = 0
    else:
        minor += 1

    new_version = f"{major}.{minor}"
    updated_source = VERSION_PATTERN.sub(
        f'VERSION = "{new_version}"',
        source,
        count=1,
    )
    VERSION_PATH.write_text(updated_source)

    print(f"Bumped version: {old_version} -> {new_version}")
    print("Next steps:")
    print("1. Run `python3 build.py`.")
    print("2. Reinstall or publish the new .xpi.")
    print("3. Commit the updated release artifacts.")
    return new_version


def show_help() -> None:
    print(__doc__)
    print()
    print("Usage: python3 bump_version.py [minor|major]")
    print("Default: minor")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in {"-h", "--help", "help"}:
        show_help()
        raise SystemExit(0)

    requested_bump = sys.argv[1] if len(sys.argv) > 1 else "minor"
    try:
        bump_version(requested_bump)
    except ValueError as exc:
        print(exc)
        raise SystemExit(1) from exc
