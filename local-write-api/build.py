#!/usr/bin/env python3
from __future__ import annotations

"""Build release artifacts for the Zotero attachment plugin."""

import hashlib
import json
import re
import zipfile
from pathlib import Path

from version import (
    ADDON_AUTHOR,
    ADDON_DESCRIPTION,
    ADDON_ID,
    ADDON_NAME,
    FULLTEXT_ATTACH_PATH,
    LOCAL_WRITE_PATH,
    REPO_URL,
    STRICT_MIN_VERSION,
    STRICT_MAX_VERSION,
    TESTED_ZOTERO_VERSION,
    UPDATE_MANIFEST_FILENAME,
    UPDATE_MANIFEST_URL,
    VERSION,
    VERSION_PATH,
    XPI_FILENAME,
    XPI_URL,
)


ROOT = Path(__file__).resolve().parent
BOOTSTRAP_PATH = ROOT / "bootstrap.js"
MANIFEST_PATH = ROOT / "manifest.json"
UPDATES_PATH = ROOT / UPDATE_MANIFEST_FILENAME
BOOTSTRAP_VAR_PATTERNS = {
    "PLUGIN_VERSION": re.compile(r'var PLUGIN_VERSION = .*?;'),
    "FULLTEXT_ATTACH_PATH": re.compile(r'var FULLTEXT_ATTACH_PATH = .*?;'),
    "LOCAL_WRITE_PATH": re.compile(r'var LOCAL_WRITE_PATH = .*?;'),
    "VERSION_PATH": re.compile(r'var VERSION_PATH = .*?;'),
    "ADDON_ID": re.compile(r'var ADDON_ID = .*?;'),
    "HOMEPAGE_URL": re.compile(r'var HOMEPAGE_URL = .*?;'),
    "UPDATE_URL": re.compile(r'var UPDATE_URL = .*?;'),
    "STRICT_MIN_VERSION": re.compile(r'var STRICT_MIN_VERSION = .*?;'),
    "STRICT_MAX_VERSION": re.compile(r'var STRICT_MAX_VERSION = .*?;'),
    "TESTED_ZOTERO_VERSION": re.compile(r'var TESTED_ZOTERO_VERSION = .*?;'),
}
BOOTSTRAP_VAR_VALUES = {
    "PLUGIN_VERSION": VERSION,
    "FULLTEXT_ATTACH_PATH": FULLTEXT_ATTACH_PATH,
    "LOCAL_WRITE_PATH": LOCAL_WRITE_PATH,
    "VERSION_PATH": VERSION_PATH,
    "ADDON_ID": ADDON_ID,
    "HOMEPAGE_URL": REPO_URL,
    "UPDATE_URL": UPDATE_MANIFEST_URL,
    "STRICT_MIN_VERSION": STRICT_MIN_VERSION,
    "STRICT_MAX_VERSION": STRICT_MAX_VERSION,
    "TESTED_ZOTERO_VERSION": TESTED_ZOTERO_VERSION,
}


def build_manifest() -> dict[str, object]:
    return {
        "manifest_version": 2,
        "name": ADDON_NAME,
        "version": VERSION,
        "description": ADDON_DESCRIPTION,
        "author": ADDON_AUTHOR,
        "homepage_url": REPO_URL,
        "icons": {"48": "icons/favicon@0.5x.png", "96": "icons/favicon.png"},
        "applications": {
            "zotero": {
                "id": ADDON_ID,
                "strict_min_version": STRICT_MIN_VERSION,
                "strict_max_version": STRICT_MAX_VERSION,
                "update_url": UPDATE_MANIFEST_URL,
            }
        },
    }


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n")


def update_bootstrap_metadata() -> None:
    bootstrap_source = BOOTSTRAP_PATH.read_text()
    updated_source = bootstrap_source
    for variable_name, pattern in BOOTSTRAP_VAR_PATTERNS.items():
        updated_source, replacements = pattern.subn(
            f"var {variable_name} = {json.dumps(BOOTSTRAP_VAR_VALUES[variable_name])};",
            updated_source,
            count=1,
        )
        if replacements != 1:
            raise RuntimeError(f"Could not update {variable_name} in bootstrap.js")
    BOOTSTRAP_PATH.write_text(updated_source)


def remove_old_xpis() -> None:
    for old_xpi in ROOT.glob("*.xpi"):
        old_xpi.unlink()


_EPOCH = (2020, 1, 1, 0, 0, 0)  # fixed timestamp for deterministic builds


def _zip_entry(arcname: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(arcname, date_time=_EPOCH)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 0
    return info


def build_xpi() -> Path:
    xpi_path = ROOT / XPI_FILENAME
    icons_dir = ROOT / "icons"
    with zipfile.ZipFile(xpi_path, "w", zipfile.ZIP_DEFLATED) as xpi:
        for path, arcname in [(MANIFEST_PATH, MANIFEST_PATH.name), (BOOTSTRAP_PATH, BOOTSTRAP_PATH.name)]:
            xpi.writestr(_zip_entry(arcname), path.read_bytes())
        if icons_dir.is_dir():
            for icon in sorted(icons_dir.iterdir()):
                if icon.is_file():
                    xpi.writestr(_zip_entry(f"icons/{icon.name}"), icon.read_bytes())
    return xpi_path


def sha256sum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_updates_manifest(xpi_hash: str) -> dict[str, object]:
    return {
        "addons": {
            ADDON_ID: {
                "updates": [
                    {
                        "version": VERSION,
                        "update_link": XPI_URL,
                        "update_hash": f"sha256:{xpi_hash}",
                        "applications": {
                            "zotero": {
                                "strict_min_version": STRICT_MIN_VERSION,
                                "strict_max_version": STRICT_MAX_VERSION,
                            }
                        },
                    }
                ]
            }
        }
    }


def build() -> Path:
    print(f"Building {ADDON_NAME} v{VERSION}")
    print(f"Zotero compatibility: {STRICT_MIN_VERSION} - {STRICT_MAX_VERSION}")
    print(f"Tested target for release gating: Zotero {TESTED_ZOTERO_VERSION}")

    update_bootstrap_metadata()
    write_json(MANIFEST_PATH, build_manifest())
    remove_old_xpis()
    xpi_path = build_xpi()
    write_json(UPDATES_PATH, build_updates_manifest(sha256sum(xpi_path)))

    print(f"Wrote {MANIFEST_PATH.name}")
    print(f"Wrote {UPDATES_PATH.name}")
    print(f"Built {xpi_path.name}")
    print(f"Published update manifest URL: {UPDATE_MANIFEST_URL}")
    print(f"Published XPI URL: {XPI_URL}")
    return xpi_path


if __name__ == "__main__":
    build()
