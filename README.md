# Zotero Attachment Plugin

Public release repo for the local Zotero add-on that powers OpenCode's attachment and write workflows.

## What It Ships

The add-on lives in [`fulltext-attach-plugin`](./fulltext-attach-plugin) and exposes three local HTTP endpoints through Zotero:

- `POST /fulltext-attach`
- `POST /opencode-zotero-write`
- `GET /opencode-zotero-plugin-version`

The version probe exists so consumers can require a minimum installed add-on version before attempting local writes.

## Compatibility

- Supported Zotero range: `7.0` to `8.0.*`
- Release target: `8.0.1`

## Release Policy

- Every shipped change bumps the minor version.
- The canonical release metadata lives in [`version.py`](./fulltext-attach-plugin/version.py).
- `python3 build.py` regenerates `manifest.json`, `updates.json`, and the versioned `.xpi`.
- The public repo publishes the rebuilt `updates.json` and `.xpi` so Zotero auto-updates can land from GitHub.

## Repo Layout

```text
fulltext-attach-plugin/   Add-on source, build scripts, manifest, update manifest, and built .xpi
examples/                 Example clients and requests
scripts/                  Utility scripts
tests/                    Add-on-specific verification assets
```

## Build

```bash
cd fulltext-attach-plugin
python3 bump_version.py
python3 build.py
```

Install the generated `.xpi` from Zotero's `Tools -> Add-ons` menu, then verify:

- `GET http://127.0.0.1:23119/opencode-zotero-plugin-version`
- `POST http://127.0.0.1:23119/fulltext-attach`
- `POST http://127.0.0.1:23119/opencode-zotero-write`
