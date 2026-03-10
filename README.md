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

## Repo Layout

```text
fulltext-attach-plugin/   Add-on source, build scripts, manifest, and update manifest
examples/                 Example clients and requests
scripts/                  Utility scripts
tests/                    Add-on-specific verification assets
```

## Build and Release

```bash
just build      # regenerate manifest.json, updates.json, and local .xpi
just release    # bump minor version, build, commit, push, create GitHub Release
```

[`version.py`](./fulltext-attach-plugin/version.py) is the single source of truth for the version number. Everything else is derived from it.

Install the generated `.xpi` from Zotero's `Tools -> Add-ons` menu, then verify:

- `GET http://127.0.0.1:23119/opencode-zotero-plugin-version`
- `POST http://127.0.0.1:23119/fulltext-attach`
- `POST http://127.0.0.1:23119/opencode-zotero-write`
