# Release Notes

This add-on is released from the public GitHub repo:

- `https://github.com/dzackgarza/zotero-attachment-plugin`

The release contract is:
- every shipped change bumps the minor version
- the repo publishes the rebuilt `.xpi`
- the repo publishes the matching `updates.json`
- the runtime API exposes `GET /opencode-zotero-plugin-version`

Compatibility target:
- supported Zotero range: `7.0` to `8.0.*`
- release target: `8.0.1`

## Release Checklist

1. Run `python3 bump_version.py`.
2. Run `python3 build.py`.
3. Commit the updated `version.py`, `manifest.json`, `updates.json`, and `.xpi`.
4. Push to the public GitHub repo.
5. In Zotero, confirm `GET /opencode-zotero-plugin-version` reports the new version.

## Expected Artifacts

Each release publishes:
- `manifest.json`
- `updates.json`
- `fulltext-attach-plugin-<version>.xpi`

## Consumer Gating

Consumers should probe `GET http://127.0.0.1:23119/opencode-zotero-plugin-version` before using write endpoints.

The probe response is the source of truth for:
- installed add-on version
- compatibility window
- update manifest location

If the endpoint is missing or the version is below the consumer's minimum required version, the consumer should stop and report that the local Zotero add-on is too old.
