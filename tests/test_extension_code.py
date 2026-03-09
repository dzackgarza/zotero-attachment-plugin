#!/usr/bin/env python3
"""
Unit tests for the extension code itself.
These tests validate the JavaScript code without requiring a running Zotero instance.
"""

import json
from pathlib import Path


class TestExtensionCode:
    """Test the extension code structure and validity."""

    def __init__(self):
        self.extension_dir = Path(__file__).parent.parent / "addon"
        self.results = []

    def test_manifest_structure(self):
        """Test that manifest.json is valid and complete."""
        print("\n1. Testing manifest.json structure...")

        manifest_path = self.extension_dir / "manifest.json"

        # Check file exists
        if not manifest_path.exists():
            print("   ❌ FAIL: manifest.json not found")
            return False

        # Parse JSON
        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
        except json.JSONDecodeError as e:
            print(f"   ❌ FAIL: Invalid JSON: {e}")
            return False

        # Check required fields
        required_fields = ["manifest_version", "name", "version", "applications"]

        missing = [f for f in required_fields if f not in manifest]
        if missing:
            print(f"   ❌ FAIL: Missing required fields: {missing}")
            return False

        # Check Zotero application block
        if "zotero" not in manifest.get("applications", {}):
            print("   ❌ FAIL: Missing applications.zotero block")
            return False

        zotero_block = manifest["applications"]["zotero"]
        if "id" not in zotero_block:
            print("   ❌ FAIL: Missing applications.zotero.id")
            return False

        # Validate ID format
        addon_id = zotero_block["id"]
        if not addon_id.endswith("@local.dev"):
            print(f"   ⚠️  WARNING: ID doesn't end with @local.dev: {addon_id}")

        print("   ✅ PASS: manifest.json is valid")
        print(f"      Name: {manifest['name']}")
        print(f"      Version: {manifest['version']}")
        print(f"      ID: {addon_id}")
        return True

    def test_bootstrap_structure(self):
        """Test that bootstrap.js has required functions."""
        print("\n2. Testing bootstrap.js structure...")

        bootstrap_path = self.extension_dir / "bootstrap.js"

        # Check file exists
        if not bootstrap_path.exists():
            print("   ❌ FAIL: bootstrap.js not found")
            return False

        # Read content
        with open(bootstrap_path, "r") as f:
            content = f.read()

        # Check required functions
        required_functions = [
            "function startup",
            "function shutdown",
            "function install",
            "function uninstall",
        ]

        missing = [f for f in required_functions if f not in content]
        if missing:
            print(f"   ❌ FAIL: Missing required functions: {missing}")
            return False

        # Check endpoint registration
        if "Zotero.Server.Endpoints" not in content:
            print("   ❌ FAIL: No endpoint registration found")
            return False

        if '"/fulltext-attach"' not in content:
            print("   ❌ FAIL: /fulltext-attach endpoint not registered")
            return False

        # Check API structure
        if "supportedMethods" not in content:
            print("   ❌ FAIL: No supportedMethods defined")
            return False

        if '"POST"' not in content:
            print("   ❌ FAIL: POST method not supported")
            return False

        print("   ✅ PASS: bootstrap.js has correct structure")
        return True

    def test_error_handling(self):
        """Test that proper error handling is in place."""
        print("\n3. Testing error handling...")

        bootstrap_path = self.extension_dir / "bootstrap.js"
        with open(bootstrap_path, "r") as f:
            content = f.read()

        # Check for try-catch blocks
        if "try {" not in content or "} catch" not in content:
            print("   ❌ FAIL: No try-catch error handling found")
            return False

        # Check for validation
        checks = [
            ("!item_key || !file_path", "input validation"),
            ("File not found", "file existence check"),
            ("Item not found", "item existence check"),
            ("sendResponse(500", "error response handling"),
        ]

        all_found = True
        for check, description in checks:
            if check in content:
                print(f"   ✅ Found: {description}")
            else:
                print(f"   ❌ Missing: {description}")
                all_found = False

        return all_found

    def test_api_calls(self):
        """Test that proper Zotero API calls are made."""
        print("\n4. Testing Zotero API usage...")

        bootstrap_path = self.extension_dir / "bootstrap.js"
        with open(bootstrap_path, "r") as f:
            content = f.read()

        # Check for required API calls
        api_calls = [
            ("Zotero.Items.getByLibraryAndKey", "item lookup"),
            ("Zotero.File.pathToFile", "file path conversion"),
            ("Zotero.Attachments.importFromFile", "file attachment"),
            ("Zotero.Fulltext.indexItems", "fulltext indexing"),
        ]

        all_found = True
        for api_call, description in api_calls:
            if api_call in content:
                print(f"   ✅ Uses: {description} ({api_call})")
            else:
                print(f"   ❌ Missing: {description} ({api_call})")
                all_found = False

        return all_found

    def test_response_format(self):
        """Test that responses match documented format."""
        print("\n5. Testing response format...")

        bootstrap_path = self.extension_dir / "bootstrap.js"
        with open(bootstrap_path, "r") as f:
            content = f.read()

        # Check success response fields
        success_fields = [
            '"success": true',
            "attachment_id",
            "attachment_key",
            "message",
        ]

        # Check error response fields
        error_fields = ['"success": false', "error", "stack"]

        print("   Success response format:")
        success_found = all(field in content for field in success_fields)
        if success_found:
            print("   ✅ All success fields present")
        else:
            print("   ❌ Missing success response fields")

        print("   Error response format:")
        error_found = all(field in content for field in error_fields)
        if error_found:
            print("   ✅ All error fields present")
        else:
            print("   ❌ Missing error response fields")

        return success_found and error_found

    def run_all_tests(self):
        """Run all tests and report results."""
        print("=" * 60)
        print("Extension Code Validation Tests")
        print("=" * 60)

        # Run tests
        results = []
        results.append(self.test_manifest_structure())
        results.append(self.test_bootstrap_structure())
        results.append(self.test_error_handling())
        results.append(self.test_api_calls())
        results.append(self.test_response_format())

        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)

        passed = sum(1 for r in results if r is True)
        failed = sum(1 for r in results if r is False)
        total = len(results)

        print(f"Total tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")

        if failed == 0:
            print("\n✅ All validation tests passed!")
            print("The extension code structure is valid.")
            return True
        else:
            print(f"\n❌ {failed} tests failed")
            print("Please fix the issues before building.")
            return False


def main():
    """Main test runner."""
    tester = TestExtensionCode()
    success = tester.run_all_tests()

    if success:
        print("\nNext steps:")
        print("1. Build the extension: python build.py")
        print("2. Install in Zotero")
        print("3. Run integration tests: python tests/test_api_endpoint.py")

    exit(0 if success else 1)


if __name__ == "__main__":
    main()
