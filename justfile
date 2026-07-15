qc-type := "bun"

# ai-review-ci contract variables consumed by doctor and workflow installers.
ai_review_ci_schema_version := "1"
ai_review_ci_profile := "bun"
ai_review_ci_ref := "main"
ai_review_ci_release_channel := "main"
ai_review_ci_workflow_template_version := "1"
ai_review_ci_local_delegation := "global-justfile"
ai_review_ci_default_branch := "main"

# Run immediate commit-tier QC
test-commit:
    @just -f ~/ai-review-ci/justfiles/bun.just -d . test-commit

# Run the full project suite before pushing
test-push:
    @just -f ~/ai-review-ci/justfiles/bun.just -d . test-push

# Run CI acceptance QC
test-ci:
    @just -f ~/ai-review-ci/justfiles/bun.just -d . test-ci

# Show the current version
version:
    @cat VERSION

# Type-check the TypeScript source
typecheck:
    bun tsc --noEmit

# Lint the TypeScript source
lint:
    bun run lint

# Compile TypeScript and build the XPI (does not bump version or release)
build:
    python3 build.py

# Live runtime proof against a real Zotero with the current XPI installed
smoke-live:
    #!/usr/bin/env bash
    set -euo pipefail
    args=()
    if [[ -n "${EXPECTED_VERSION:-}" ]]; then
        args+=(--expected-version "${EXPECTED_VERSION}")
    fi
    if [[ -n "${ZOTERO_LOCAL_BASE_URL:-}" ]]; then
        args+=(--base-url "${ZOTERO_LOCAL_BASE_URL}")
    fi
    if [[ -n "${ZOTERO_LIBRARY_ID:-}" ]]; then
        args+=(--library-id "${ZOTERO_LIBRARY_ID}")
    fi
    python3 examples/live_smoke.py "${args[@]}"

# Build the working-tree XPI and hot-install it into a Zotero profile, then
# restart Zotero with a cache purge so the current code is actually loaded, and
# wait until the add-on answers with the built version and its capabilities.
#
# This REPLACES the running add-on and RESTARTS Zotero (closing the current
# session). updates.json is a release channel, not a reliable local same-version
# reload, so the proven path is replace-profile-XPI + restart (AGENTS.md).
#
# This is the ONLY install path. Locally it targets the active Default=1 profile;
# CI sets ZOTERO_PROFILE_DIR (and ZOTERO_PROFILE_NAME, passed to -P) to target a
# disposable profile. The build -> byte-compare -> purgecache-restart -> version
# wait sequence is what catches the stale-build trap, so CI must not re-implement
# it: a second copy that drifts would prove something different from local.
#   ZOTERO_PROFILE_DIR   override the profile directory (default: Default=1)
#   ZOTERO_PROFILE_NAME  profile name for `zotero -P` (default: none)
[doc("Build, install, and restart Zotero so the working-tree XPI is live (RESTARTS Zotero)")]
install-live:
    #!/usr/bin/env bash
    set -euo pipefail
    version="$(cat VERSION)"
    xpi="local-write-api-${version}.xpi"

    # 1. Build from the working tree.
    python3 build.py
    test -f "$xpi" || { echo "expected $xpi was not built" >&2; exit 1; }

    # 2. Resolve the target profile: CI provides one, otherwise Default=1.
    profile_dir="${ZOTERO_PROFILE_DIR:-$(just _default-profile-dir)}"
    test -d "$profile_dir" || { echo "profile dir not found: $profile_dir" >&2; exit 1; }
    ext_dir="${profile_dir}/extensions"
    installed="${ext_dir}/local-write-api@dzackgarza.com.xpi"

    # 3. Timestamped backup of the currently installed XPI.
    if [[ -f "$installed" ]]; then
        cp -p "$installed" "${installed}.bak.$(date +%Y%m%d-%H%M%S)"
    fi

    # 4. Install and verify the installed bytes match the build exactly. A
    #    matching version string is NOT proof when rebuilding the same version.
    mkdir -p "$ext_dir"
    cp "$xpi" "$installed"
    if [[ "$(sha256sum "$xpi" | cut -d' ' -f1)" != "$(sha256sum "$installed" | cut -d' ' -f1)" ]]; then
        echo "sha256 mismatch after install" >&2
        exit 1
    fi
    echo "installed $xpi -> $installed"

    # 5. Restart Zotero with cache purge. Stop by exact process name (-x), never
    #    pkill -f, whose pattern would match this recipe's own shell (AGENTS.md).
    pkill -x zotero-bin || true
    pkill -x zotero || true
    sleep 3
    profile_args=()
    if [[ -n "${ZOTERO_PROFILE_NAME:-}" ]]; then
        profile_args+=(-P "${ZOTERO_PROFILE_NAME}")
    fi
    log="${ZOTERO_LOG:-/tmp/zotero-local-write-api-zotero.log}"
    setsid env \
        DISPLAY="${DISPLAY:-:0}" \
        WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-1}" \
        XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}" \
        DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus}" \
        zotero "${profile_args[@]}" -purgecaches >"$log" 2>&1 < /dev/null &

    # 6. Wait for the add-on to answer with the just-built version AND the
    #    capabilities the proofs rely on. Version alone would pass against a
    #    build that dropped an endpoint.
    base="${ZOTERO_LOCAL_BASE_URL:-http://127.0.0.1:23119}"
    probe="$(mktemp)"
    trap 'rm -f "$probe"' EXIT
    for _ in $(seq 1 60); do
        if curl -fsS "$base/version" -o "$probe" 2>/dev/null; then
            if python3 -c '
    import json, sys
    probe, expected = sys.argv[1], sys.argv[2]
    v = json.load(open(probe))
    if v.get("version") != expected:
        sys.exit(1)
    required = {"attach", "attach_bytes", "write", "version_probe", "import_bibtex"}
    missing = required - set(v.get("capabilities") or [])
    if missing:
        sys.exit(f"add-on is missing capabilities: {sorted(missing)}")
    ' "$probe" "$version"; then
                echo "Zotero up with version $version — run 'EXPECTED_VERSION=$version just smoke-live' to prove behavior"
                exit 0
            fi
        fi
        sleep 2
    done
    echo "Zotero did not report version $version within timeout; see $log" >&2
    exit 1

# Path of the active (Default=1) Zotero profile directory.
[private]
_default-profile-dir:
    #!/usr/bin/env python3
    # profiles.ini is INI, so it is parsed with configparser rather than matched
    # with a line-order-dependent regex: Default= and Path= may appear in either
    # order within a section, and only [Profile*] sections carry Default=1 (an
    # [Install*] section's Default= is a path, not a flag).
    import configparser, pathlib, sys

    ini = pathlib.Path.home() / ".zotero/zotero/profiles.ini"
    if not ini.is_file():
        sys.exit(f"no profiles.ini at {ini}")
    cfg = configparser.ConfigParser()
    cfg.read(ini)
    for name in cfg.sections():
        section = cfg[name]
        if "Path" not in section or section.get("Default", "").strip() != "1":
            continue
        path = pathlib.Path(section["Path"])
        if section.get("IsRelative", "1").strip() == "1":
            path = ini.parent / path
        print(path)
        break
    else:
        sys.exit(f"no Default=1 profile with a Path in {ini}")

# Static OpenAPI contract check (lint + generated-drift + dispatch conformance)
openapi-check:
    bun run openapi:check

# Generic Schemathesis fuzzing against a live Zotero.
# MUTATING: point ZOTERO_LOCAL_BASE_URL at a disposable test profile, never a
# real library. The filter_case hook excludes dangerous/networked/bulk ops.
[doc("Generic Schemathesis fuzz against a live Zotero (MUTATING: use a disposable profile)")]
schemathesis-fuzz-live:
    #!/usr/bin/env bash
    set -euo pipefail
    url="${ZOTERO_LOCAL_BASE_URL:-http://127.0.0.1:23119}"
    export PYTHONPATH="${PYTHONPATH:-}:."
    export SCHEMATHESIS_HOOKS="tests.schemathesis.hooks"
    # A fixed seed for a reproducible run, then a randomized exploration run.
    # Both emit JUnit + HAR reproduction artifacts. The stateful workflow runs
    # separately via schemathesis-stateful-live.
    for seed in "--seed 0" ""; do
        uv run st run openapi.yaml --url "$url" \
            --phases examples,coverage,fuzzing \
            ${seed} \
            --report junit,har --report-dir schemathesis-report
    done

# Live proof of the generated OpenAPI client wrapper (src/client.ts) against a
# real Zotero: real POST /write, body serialized unchanged, typed success/error
# split. MUTATING, so it is opt-in via ZOTERO_LIVE and is never collected by
# ordinary `bun test`; objects are uniquely prefixed and trashed afterwards.
[doc("Live proof of the generated TypeScript client wrapper (MUTATING, opt-in)")]
client-live:
    ZOTERO_LIVE=1 bun test tests/client-live.test.ts

# Stateful create/note/collection/tag/merge/restore/trash proof with Zotero
# read-back. Safe against a real library: unique-prefixed objects, cleanup in
# teardown. Skips when no live add-on is reachable.
[doc("Stateful create/merge/restore/trash workflow proof against a live Zotero")]
schemathesis-stateful-live:
    uv run pytest tests/schemathesis/test_stateful.py -q

# Full live API proof: generic fuzz, stateful workflow, client wrapper, smoke.
api-live: schemathesis-fuzz-live schemathesis-stateful-live client-live smoke-live

# Run all checks (typecheck + lint)
check: typecheck lint

# Release a patch version — bug fixes, infra, tooling (default)
release: (_release "patch")

# Release a minor version — new features or behaviour changes
release-minor: (_release "minor")

# Release a major version — breaking release line
release-major: (_release "major")

# Regenerate plugin icons via Replicate (requires REPLICATE_API_TOKEN in env)
# Run this, commit src/icons/, then cut a release.
[doc("Regenerate plugin icons via Replicate (requires REPLICATE_API_TOKEN)")]
gen-icons:
    #!/usr/bin/env python3
    import os, time, urllib.request, json
    from pathlib import Path

    token = os.environ.get("REPLICATE_API_TOKEN") or open(os.path.expanduser("~/.envrc")).read().split("REPLICATE_API_TOKEN=")[1].split("\n")[0]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    prompt = (
        "minimal flat icon design, open book with a small electrical plug connector, "
        "dark red and white color scheme, clean geometric shapes, centered, no text, "
        "white background, icon style, vector-like"
    )
    payload = json.dumps({"input": {"prompt": prompt, "aspect_ratio": "1:1", "output_format": "png", "go_fast": True}}).encode()
    req = urllib.request.Request("https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions", data=payload, headers=headers, method="POST")
    pred_id = json.loads(urllib.request.urlopen(req).read())["id"]
    print(f"Prediction {pred_id} — waiting...")

    for _ in range(30):
        time.sleep(3)
        req = urllib.request.Request(f"https://api.replicate.com/v1/predictions/{pred_id}", headers=headers)
        resp = json.loads(urllib.request.urlopen(req).read())
        if resp["status"] == "succeeded":
            img_url = resp["output"][0]
            break
        elif resp["status"] == "failed":
            raise RuntimeError(f"Prediction failed: {resp}")
    else:
        raise TimeoutError("Timed out waiting for prediction")

    from PIL import Image
    import urllib.request as ul
    raw = Image.open(ul.urlopen(img_url)).convert("RGBA")
    icons = Path("src/icons")
    icons.mkdir(exist_ok=True)
    raw.resize((96, 96), Image.LANCZOS).save(icons / "favicon.png")
    raw.resize((48, 48), Image.LANCZOS).save(icons / "favicon@0.5x.png")
    print("Wrote src/icons/favicon.png (96x96) and src/icons/favicon@0.5x.png (48x48)")

# --- private ---

_bump bump_type:
    #!/usr/bin/env python3
    import re, sys
    from pathlib import Path
    path = Path("VERSION")
    source = path.read_text().strip()
    m = re.match(r'^(\d+)\.(\d+)\.(\d+)$', source)
    if not m:
        sys.exit('Could not parse X.Y.Z from VERSION')
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if "{{bump_type}}" == "major":
        major, minor, patch = major + 1, 0, 0
    elif "{{bump_type}}" == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    new = f"{major}.{minor}.{patch}"
    path.write_text(new + "\n")
    print(f"Bumped to {new}")

_release bump_type: (_bump bump_type)
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Required before tagging: install the current working-tree XPI and run 'just smoke-live'" >&2
    bun run typecheck
    bun run lint
    python3 build.py
    version=$(cat VERSION)
    git add VERSION updates.json
    git commit -m "chore: release v${version}"
    git tag "v${version}"
    git push
    git push --tags
    echo "v${version} tagged — Actions will publish the release"
