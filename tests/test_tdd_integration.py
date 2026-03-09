#!/usr/bin/env python3
"""
Fail-first TDD test suite for Fulltext Attachment API.
Tests should fail initially, then pass after implementation.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

# Test configuration
ZOTERO_API_BASE = "http://localhost:23119"
FULLTEXT_ENDPOINT = f"{ZOTERO_API_BASE}/fulltext-attach"
EXTENSION_DIR = Path(__file__).parent.parent


class TestTDD:
    """TDD test cases - designed to fail first."""

    def __init__(self):
        self.test_item_key = None  # Will be discovered dynamically
        self.temp_dir = tempfile.mkdtemp(prefix="zotero_tdd_test_")

    def check_zotero_running(self):
        """Verify Zotero is running - MUST be true for all tests."""
        try:
            response = requests.get(f"{ZOTERO_API_BASE}/", timeout=5)
            # Zotero returns 404 "No endpoint found" when running - that's expected
            if response.status_code == 404 and "No endpoint found" in response.text:
                return True
            elif response.status_code == 200:
                return True
            else:
                print("❌ FATAL: Zotero is not running!")
                print("   Start Zotero before running tests.")
                raise ConnectionError("Zotero is not running or API is inaccessible")
        except requests.exceptions.ConnectionError:
            print("❌ FATAL: Cannot connect to Zotero on port 23119!")
            print("   Start Zotero before running tests.")
            raise ConnectionError("Cannot connect to Zotero API")

    def get_or_create_test_item(self):
        """Get an existing item or create one for testing."""
        # Try to find an existing non-attachment item
        try:
            response = requests.get(
                f"{ZOTERO_API_BASE}/api/library/items?itemType=-attachment&limit=1",
                timeout=10,
            )
            if response.status_code == 200:
                items = response.json()
                if items:
                    self.test_item_key = items[0]["key"]
                    print(f"✅ Using existing test item: {self.test_item_key}")
                    return self.test_item_key
        except Exception as e:
            print(f"Error getting existing item: {e}")

        # If no items found, we can't create via read-only API
        print("❌ No suitable test items found in library")
        print(
            "   Please ensure your Zotero library has at least one non-attachment item"
        )
        raise ValueError("No test items available")

    def test_1_endpoint_not_found_before_install(self):
        """Test 1: Endpoint should return 404 before extension is installed."""
        print("\nTest 1: Endpoint should NOT exist before installation")
        print("-" * 50)

        try:
            response = requests.post(
                FULLTEXT_ENDPOINT, json={"test": "data"}, timeout=5
            )

            if response.status_code == 404 or "No endpoint found" in response.text:
                print("✅ PASS: Endpoint correctly returns 404 (not installed)")
                return True
            else:
                print(f"❌ FAIL: Expected 404, got {response.status_code}")
                print(f"   Response: {response.text[:100]}")
                print("   Extension might already be installed!")
                return False

        except requests.exceptions.ConnectionError:
            # This could mean Zotero isn't running
            self.check_zotero_running()
            return False

    def test_2_build_extension(self):
        """Test 2: Extension should build successfully."""
        print("\nTest 2: Build extension")
        print("-" * 50)

        build_script = EXTENSION_DIR / "build.py"

        # Run build
        result = subprocess.run(
            [sys.executable, str(build_script), "build"], capture_output=True, text=True
        )

        if result.returncode == 0:
            # Check if .xpi was created
            xpi_files = list(EXTENSION_DIR.glob("*.xpi"))
            if xpi_files:
                print("✅ PASS: Extension built successfully")
                print(f"   Created: {xpi_files[0].name}")
                return True
            else:
                print("❌ FAIL: Build succeeded but no .xpi file found")
                return False
        else:
            print(f"❌ FAIL: Build failed with code {result.returncode}")
            print(f"   Error: {result.stderr}")
            return False

    def test_3_install_extension(self):
        """Test 3: Extension installation instructions."""
        print("\nTest 3: Manual installation required")
        print("-" * 50)

        xpi_files = list(EXTENSION_DIR.glob("*.xpi"))
        if not xpi_files:
            print("❌ FAIL: No .xpi file found to install")
            return False

        xpi_path = xpi_files[0].absolute()

        print("⚠️  MANUAL STEP REQUIRED:")
        print("\n1. In Zotero, go to: Tools → Add-ons")
        print("2. Click gear icon → Install Add-on From File...")
        print(f"3. Select: {xpi_path}")
        print("4. Click 'Install'")
        print("5. Restart Zotero if prompted")
        print("\nPress Enter when installation is complete...")

        input()

        # Give Zotero time to restart
        print("Waiting for Zotero to be ready...")
        time.sleep(3)

        # Verify Zotero is still running
        self.check_zotero_running()

        print("✅ Assuming installation completed")
        return True

    def test_4_endpoint_exists_after_install(self):
        """Test 4: Endpoint should be available after installation."""
        print("\nTest 4: Endpoint should exist after installation")
        print("-" * 50)

        try:
            # Send invalid request to test endpoint exists
            response = requests.post(
                FULLTEXT_ENDPOINT,
                json={},  # Empty data should trigger validation error
                timeout=5,
            )

            if response.status_code == 404:
                print("❌ FAIL: Endpoint still returns 404 after installation")
                print("   Extension may not be properly installed or loaded")
                return False

            # We expect 500 error for invalid data, not 404
            if response.status_code == 500:
                result = response.json()
                if "Missing required fields" in result.get("error", ""):
                    print("✅ PASS: Endpoint exists and validates input")
                    return True
                else:
                    print(f"✅ PASS: Endpoint exists (got {response.status_code})")
                    return True
            else:
                print(f"⚠️  Unexpected response: {response.status_code}")
                print(f"   Body: {response.text[:200]}")
                # Still pass if not 404
                return response.status_code != 404

        except Exception as e:
            print(f"❌ FAIL: Error testing endpoint: {e}")
            return False

    def test_5_attachment_with_nonexistent_file(self):
        """Test 5: Should fail with non-existent file."""
        print("\nTest 5: Attachment should fail with non-existent file")
        print("-" * 50)

        if not self.test_item_key:
            print("   ⚠️  SKIP: No test item available")
            return None

        try:
            response = requests.post(
                FULLTEXT_ENDPOINT,
                json={
                    "item_key": self.test_item_key,
                    "file_path": "/tmp/this_file_definitely_does_not_exist_12345.txt",
                },
                timeout=10,
            )

            if response.status_code == 500:
                result = response.json()
                if "File not found" in result.get("error", ""):
                    print("✅ PASS: Correctly rejected non-existent file")
                    return True
                else:
                    print(f"❌ FAIL: Got 500 but wrong error: {result.get('error')}")
                    return False
            else:
                print(f"❌ FAIL: Expected 500 error, got {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ FAIL: Error in test: {e}")
            return False

    def test_6_attachment_with_invalid_item(self):
        """Test 6: Should fail with invalid item key."""
        print("\nTest 6: Attachment should fail with invalid item key")
        print("-" * 50)

        # Create a real test file
        test_file = os.path.join(self.temp_dir, "test_invalid_item.txt")
        with open(test_file, "w") as f:
            f.write("Test content for invalid item")

        try:
            response = requests.post(
                FULLTEXT_ENDPOINT,
                json={
                    "item_key": "INVALID_KEY_THAT_DOES_NOT_EXIST",
                    "file_path": test_file,
                },
                timeout=10,
            )

            if response.status_code == 500:
                result = response.json()
                if "Item not found" in result.get("error", ""):
                    print("✅ PASS: Correctly rejected invalid item key")
                    return True
                else:
                    print(f"❌ FAIL: Got 500 but wrong error: {result.get('error')}")
                    return False
            else:
                print(f"❌ FAIL: Expected 500 error, got {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ FAIL: Error in test: {e}")
            return False

    def test_7_successful_attachment(self):
        """Test 7: Should successfully attach file to valid item."""
        print("\nTest 7: Successful file attachment")
        print("-" * 50)

        if not self.test_item_key:
            print("   ⚠️  SKIP: No test item available")
            return None

        # Create test file with specific content
        test_content = """Test Fulltext Content
Mathematical expression: Γrhas 19 roots
Special characters: α β γ δ ε
Multiple lines of text
End of test content"""

        test_file = os.path.join(self.temp_dir, "test_successful.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)

        print(f"Created test file: {test_file}")
        print(f"Using item key: {self.test_item_key}")

        try:
            response = requests.post(
                FULLTEXT_ENDPOINT,
                json={
                    "item_key": self.test_item_key,
                    "file_path": test_file,
                    "title": "TDD Test Fulltext",
                },
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print("✅ PASS: Successfully attached file!")
                    print(f"   Attachment ID: {result.get('attachment_id')}")
                    print(f"   Attachment Key: {result.get('attachment_key')}")
                    print(f"   Message: {result.get('message')}")
                    return True
                else:
                    print(f"❌ FAIL: Got 200 but success=false: {result}")
                    return False
            else:
                print(f"❌ FAIL: Expected 200, got {response.status_code}")
                result = response.json()
                print(f"   Error: {result.get('error')}")
                return False

        except Exception as e:
            print(f"❌ FAIL: Error in test: {e}")
            return False

    def test_8_verify_in_zotero(self):
        """Test 8: Verification instructions."""
        print("\nTest 8: Manual verification in Zotero")
        print("-" * 50)

        if not self.test_item_key:
            print("   ⚠️  SKIP: No test item available")
            return None

        print("⚠️  MANUAL VERIFICATION:")
        print(f"\n1. In Zotero, find item with key: {self.test_item_key}")
        print("2. Look for attachment titled 'TDD Test Fulltext'")
        print("3. Double-click to open the attachment")
        print("4. Verify it contains 'Γrhas 19 roots'")
        print("\nDid the attachment appear correctly? (y/n): ", end="")

        response = input().strip().lower()

        if response == "y":
            print("✅ PASS: Attachment verified in Zotero")
            return True
        else:
            print("❌ FAIL: Attachment not found or incorrect")
            return False

    def cleanup(self):
        """Clean up test files."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil

            shutil.rmtree(self.temp_dir)

    def run_all_tests(self):
        """Run all TDD tests in sequence."""
        print("=" * 60)
        print("TDD Integration Test Suite")
        print("Fail-First Test Driven Development")
        print("=" * 60)

        # Verify Zotero is running
        try:
            self.check_zotero_running()
            print("✅ Zotero is running")
        except ConnectionError as e:
            print(f"\n❌ ERROR: {e}")
            print("Please start Zotero before running tests.")
            return False

        # Define test sequence
        tests = [
            self.test_1_endpoint_not_found_before_install,
            self.test_2_build_extension,
            self.test_3_install_extension,
            self.test_4_endpoint_exists_after_install,
            self.test_5_attachment_with_nonexistent_file,
            self.test_6_attachment_with_invalid_item,
            self.test_7_successful_attachment,
            self.test_8_verify_in_zotero,
        ]

        results = []

        # Run tests in sequence
        for i, test in enumerate(tests, 1):
            try:
                # Get test item before tests that need it (tests 5-8)
                if i >= 5 and not self.test_item_key:
                    try:
                        self.get_or_create_test_item()
                    except ValueError as e:
                        print(f"\n⚠️  WARNING: {e}")
                        print("   Tests requiring item key will be skipped")

                result = test()
                results.append(result)

                # Stop on critical failures
                if not result and i <= 4:  # First 4 tests are critical
                    print(f"\n❌ Stopping: Test {i} is critical and failed")
                    break

            except KeyboardInterrupt:
                print("\n\n⚠️  Tests interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error in test {i}: {e}")
                results.append(False)

        # Summary
        print("\n" + "=" * 60)
        print("TDD Test Summary")
        print("=" * 60)

        for i, (test, result) in enumerate(zip(tests[: len(results)], results), 1):
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"Test {i}: {status} - {test.__doc__.strip()}")

        passed = sum(1 for r in results if r)
        failed = sum(1 for r in results if not r)
        total = len(results)

        print(f"\nTotal: {total}, Passed: {passed}, Failed: {failed}")

        if failed == 0 and total == len(tests):
            print("\n🎉 All tests passed! Extension is working correctly.")
            return True
        else:
            print(f"\n❌ {failed} test(s) failed or {len(tests) - total} not run")
            return False


def main():
    """Main test runner."""
    print("Starting TDD test suite...")
    print("This will test the extension from scratch.\n")

    tester = TestTDD()
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        tester.cleanup()


if __name__ == "__main__":
    main()
