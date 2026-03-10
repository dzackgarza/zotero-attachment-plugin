plugin_dir := "fulltext-attach-plugin"

# Show the current version
version:
    @cd {{plugin_dir}} && python3 -c "from version import VERSION; print(VERSION)"

# Regenerate manifest.json, updates.json, and the local .xpi from version.py
build:
    cd {{plugin_dir}} && python3 build.py

# Bump the minor version in version.py (standard release bump)
bump:
    cd {{plugin_dir}} && python3 bump_version.py minor

# Bump the major version in version.py
bump-major:
    cd {{plugin_dir}} && python3 bump_version.py major

# Release a new minor version: bump, build, commit metadata, push, create GitHub Release with .xpi
release:
    #!/usr/bin/env bash
    set -euo pipefail
    cd {{plugin_dir}}
    python3 bump_version.py minor
    python3 build.py
    version=$(python3 -c "from version import VERSION; print(VERSION)")
    xpi="fulltext-attach-plugin-${version}.xpi"
    cd ..
    git add {{plugin_dir}}/version.py {{plugin_dir}}/manifest.json {{plugin_dir}}/updates.json
    git commit -m "chore: release v${version}"
    git push
    gh release create "v${version}" \
        --title "v${version}" \
        --generate-notes \
        "{{plugin_dir}}/${xpi}#Zotero add-on (.xpi)"
    echo "Released v${version}: https://github.com/dzackgarza/zotero-attachment-plugin/releases/tag/v${version}"

# Release a new major version: bump major, build, commit metadata, push, create GitHub Release
release-major:
    #!/usr/bin/env bash
    set -euo pipefail
    cd {{plugin_dir}}
    python3 bump_version.py major
    python3 build.py
    version=$(python3 -c "from version import VERSION; print(VERSION)")
    xpi="fulltext-attach-plugin-${version}.xpi"
    cd ..
    git add {{plugin_dir}}/version.py {{plugin_dir}}/manifest.json {{plugin_dir}}/updates.json
    git commit -m "chore: major release v${version}"
    git push
    gh release create "v${version}" \
        --title "v${version}" \
        --generate-notes \
        "{{plugin_dir}}/${xpi}#Zotero add-on (.xpi)"
    echo "Released v${version}: https://github.com/dzackgarza/zotero-attachment-plugin/releases/tag/v${version}"
