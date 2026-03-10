# Fulltext Attachment API for Zotero

This add-on exposes local HTTP endpoints on Zotero's desktop server so external tools can attach files and perform OpenCode-specific library writes.

Compatibility:
- Supported window: Zotero `7.0` through `8.0.x`
- Release target: Zotero `8.0.1`

## Endpoints

### `POST /fulltext-attach`

Attach a local file to an existing Zotero item as a stored attachment.

Request body:

```json
{
  "item_key": "ABC123XYZ",
  "file_path": "/absolute/path/to/file.pdf",
  "title": "Attachment Title"
}
```

### `POST /opencode-zotero-write`

Run the add-on's local write bridge for existing-item metadata, tags, collections, attachments, and notes.

Request body:

```json
{
  "operation": "update_item_fields",
  "data": {
    "item_key": "ABC123XYZ",
    "fields": {
      "title": "Updated Title"
    }
  }
}
```

### `GET /opencode-zotero-plugin-version`

Return the installed add-on version and compatibility metadata so consumers can gate on a minimum required version.

Example response:

```json
{
  "success": true,
  "version": "3.1",
  "addon_id": "fulltext-attach-api-v3@local.dev",
  "homepage_url": "https://github.com/dzackgarza/zotero-attachment-plugin",
  "update_url": "https://raw.githubusercontent.com/dzackgarza/zotero-attachment-plugin/main/fulltext-attach-plugin/updates.json",
  "endpoints": {
    "fulltext_attach": "/fulltext-attach",
    "local_write": "/opencode-zotero-write",
    "version": "/opencode-zotero-plugin-version"
  },
  "compatibility": {
    "strict_min_version": "7.0",
    "strict_max_version": "8.0.*",
    "tested_zotero_version": "8.0.1"
  },
  "capabilities": [
    "fulltext_attach",
    "local_write",
    "version_probe"
  ]
}
```

## Build and Release

From the repo root:

```bash
just build      # regenerate manifest.json, updates.json, and local .xpi
just release    # bump minor version, build, commit, push, create GitHub Release
```

[`version.py`](./version.py) is the single source of truth for the version number, repo URLs, compatibility window, and endpoint paths. All generated artifacts derive from it.

## Install

Download the `.xpi` from the [latest GitHub Release](https://github.com/dzackgarza/zotero-attachment-plugin/releases/latest).

1. In Zotero, open `Tools -> Add-ons`.
2. Choose `Install Add-on From File...`.
3. Select the downloaded `.xpi`.

After installation, verify:
- `GET http://127.0.0.1:23119/opencode-zotero-plugin-version` returns the expected version
- `POST http://127.0.0.1:23119/fulltext-attach` is reachable
- `POST http://127.0.0.1:23119/opencode-zotero-write` is reachable
