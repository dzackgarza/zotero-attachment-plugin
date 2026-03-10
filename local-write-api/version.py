#!/usr/bin/env python3
"""Canonical release metadata for the Zotero attachment plugin."""

VERSION = "3.1.8"

REPO_OWNER = "dzackgarza"
REPO_NAME = "zotero-attachment-plugin"
REPO_BRANCH = "main"

ADDON_ID = "local-write-api@dzackgarza.com"
ADDON_SLUG = "local-write-api"
ADDON_NAME = "Local Write API"
ADDON_AUTHOR = "D. Zack Garza"
ADDON_DESCRIPTION = (
    "Exposes write endpoints on Zotero's local HTTP server, covering the gap left by the read-only built-in API."
)

STRICT_MIN_VERSION = "7.0"
STRICT_MAX_VERSION = "*"
TESTED_ZOTERO_VERSION = "8.0.1"

FULLTEXT_ATTACH_PATH = "/attach"
LOCAL_WRITE_PATH = "/write"
VERSION_PATH = "/version"

REPO_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}"
RAW_BASE_URL = (
    f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{REPO_BRANCH}/{ADDON_SLUG}"
)
UPDATE_MANIFEST_FILENAME = "updates.json"
UPDATE_MANIFEST_URL = f"{RAW_BASE_URL}/{UPDATE_MANIFEST_FILENAME}"
XPI_FILENAME = f"{ADDON_SLUG}-{VERSION}.xpi"
XPI_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/download/v{VERSION}/{XPI_FILENAME}"
