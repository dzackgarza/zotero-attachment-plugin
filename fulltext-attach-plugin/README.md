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

## Build

Run from [`fulltext-attach-plugin`](./):

```bash
python3 build.py
```

This regenerates:
- `manifest.json`
- `updates.json`
- `fulltext-attach-plugin-<version>.xpi`

The build uses [`version.py`](./version.py) as the source of truth for:
- add-on version
- repo URLs
- Zotero compatibility window
- endpoint paths

## Versioning Policy

Every shipped plugin change must bump the minor version.

Use:

```bash
python3 bump_version.py
```

Valid bump types:
- `minor` for normal changes
- `major` for breaking release lines

`patch` bumps are intentionally rejected.

## GitHub Updates

Auto-update metadata is published from the public repo:

- Repo: `https://github.com/dzackgarza/zotero-attachment-plugin`
- Update manifest: `https://raw.githubusercontent.com/dzackgarza/zotero-attachment-plugin/main/fulltext-attach-plugin/updates.json`

For Zotero auto-updates to work, the repo must publish both:
- the rebuilt `updates.json`
- the rebuilt versioned `.xpi`

## Install

1. Build the add-on with `python3 build.py`.
2. In Zotero, open `Tools -> Add-ons`.
3. Choose `Install Add-on From File...`.
4. Select the generated `.xpi`.

After installation, verify:
- `GET http://127.0.0.1:23119/opencode-zotero-plugin-version` returns the expected version
- `POST http://127.0.0.1:23119/fulltext-attach` is reachable
- `POST http://127.0.0.1:23119/opencode-zotero-write` is reachable
