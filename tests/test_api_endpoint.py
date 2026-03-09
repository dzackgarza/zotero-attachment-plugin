#!/usr/bin/env python3
"""
Test suite for the Fulltext Attachment API endpoint.
Tests HTTP API functionality with a running Zotero instance.
"""

import os
import sys
import tempfile
from pathlib import Path

import requests

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Test configuration
ZOTERO_API_BASE = "http://localhost:23119"
FULLTEXT_ENDPOINT = f"{ZOTERO_API_BASE}/fulltext-attach"
TEST_TIMEOUT = 30


class TestFulltextAttachAPI:
    """Test cases for the fulltext attachment API endpoint."""

    def __init__(self):
        self.test_item_key = None
        self.test_file_path = None
        self.temp_dir = tempfile.mkdtemp(prefix="zotero_test_")

    def cleanup(self):
        """Clean up test files."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil

            shutil.rmtree(self.temp_dir)

    def check_zotero_running(self):
        """Check if Zotero is running and accessible."""
        try:
            response = requests.get(f"{ZOTERO_API_BASE}/api/config", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def create_test_file(self, content="Test fulltext content\nΓrhas 19 roots"):
        """Create a test file with content."""
        test_file = os.path.join(self.temp_dir, "test_fulltext.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(content)
        self.test_file_path = test_file
        return test_file

    def get_test_item_key(self):
        """Get a test item key from Zotero library."""
        # First try to get an existing item
        try:
            response = requests.get(
                f"{ZOTERO_API_BASE}/api/library/items?itemType=-attachment", timeout=10
            )
            if response.status_code == 200:
                items = response.json()
                if items:
                    # Use the first non-attachment item
                    self.test_item_key = items[0]["key"]
                    return self.test_item_key
        except Exception as e:
            print(f"Error getting test item: {e}")

        return None

    def test_endpoint_exists(self):
        """Test that the endpoint is registered."""
        print("\n1. Testing endpoint registration...")

        # Send OPTIONS request to check if endpoint exists
        try:
            response = requests.options(FULLTEXT_ENDPOINT, timeout=5)
            # Even if OPTIONS isn't supported, we should get something other than 404
            if response.status_code == 404:
                print("   ❌ FAIL: Endpoint not found (404)")
                return False
            else:
                print("   ✅ PASS: Endpoint is registered")
                return True
        except requests.exceptions.ConnectionError:
            print("   ❌ FAIL: Cannot connect to Zotero. Is it running?")
            return False
        except Exception as e:
            print(f"   ❌ FAIL: {str(e)}")
            return False

    def test_post_method(self):
        """Test POST method support."""
        print("\n2. Testing POST method support...")

        # Send empty POST to test method support
        try:
            response = requests.post(FULLTEXT_ENDPOINT, json={}, timeout=5)
            # We expect an error about missing fields, not method not allowed
            if response.status_code == 405:
                print("   ❌ FAIL: POST method not allowed")
                return False
            else:
                print("   ✅ PASS: POST method is supported")
                return True
        except Exception as e:
            print(f"   ❌ FAIL: {str(e)}")
            return False

    def test_validation_missing_fields(self):
        """Test validation of missing required fields."""
        print("\n3. Testing field validation...")

        test_cases = [
            ({}, "empty request"),
            ({"item_key": "TEST123"}, "missing file_path"),
            ({"file_path": "/tmp/test.txt"}, "missing item_key"),
        ]

        all_passed = True
        for data, description in test_cases:
            try:
                response = requests.post(FULLTEXT_ENDPOINT, json=data, timeout=5)
                result = response.json()

                if response.status_code == 500 and not result.get("success", True):
                    print(f"   ✅ PASS: Correctly rejected {description}")
                else:
                    print(f"   ❌ FAIL: Should have rejected {description}")
                    all_passed = False
            except Exception as e:
                print(f"   ❌ FAIL: Error testing {description}: {str(e)}")
                all_passed = False

        return all_passed

    def test_file_not_found(self):
        """Test handling of non-existent file."""
        print("\n4. Testing non-existent file handling...")

        if not self.test_item_key:
            print("   ⚠️  SKIP: No test item available")
            return None

        try:
            response = requests.post(
                FULLTEXT_ENDPOINT,
                json={
                    "item_key": self.test_item_key,
                    "file_path": "/tmp/definitely_does_not_exist_12345.txt",
                },
                timeout=10,
            )
            result = response.json()

            if response.status_code == 500 and "File not found" in result.get(
                "error", ""
            ):
                print("   ✅ PASS: Correctly handled non-existent file")
                return True
            else:
                print(f"   ❌ FAIL: Unexpected response: {result}")
                return False
        except Exception as e:
            print(f"   ❌ FAIL: {str(e)}")
            return False

    def test_invalid_item_key(self):
        """Test handling of invalid item key."""
        print("\n5. Testing invalid item key handling...")

        # Create test file
        test_file = self.create_test_file()

        try:
            response = requests.post(
                FULLTEXT_ENDPOINT,
                json={
                    "item_key": "DEFINITELY_INVALID_KEY_12345",
                    "file_path": test_file,
                },
                timeout=10,
            )
            result = response.json()

            if response.status_code == 500 and "Item not found" in result.get(
                "error", ""
            ):
                print("   ✅ PASS: Correctly handled invalid item key")
                return True
            else:
                print(f"   ❌ FAIL: Unexpected response: {result}")
                return False
        except Exception as e:
            print(f"   ❌ FAIL: {str(e)}")
            return False

    def test_successful_attachment(self):
        """Test successful file attachment."""
        print("\n6. Testing successful attachment...")

        if not self.test_item_key:
            print("   ⚠️  SKIP: No test item available")
            return None

        # Create test file with specific content
        test_content = (
            "Test fulltext content\nΓrhas 19 roots\nMathematical expressions preserved"
        )
        test_file = self.create_test_file(test_content)

        try:
            response = requests.post(
                FULLTEXT_ENDPOINT,
                json={
                    "item_key": self.test_item_key,
                    "file_path": test_file,
                    "title": "Test Fulltext Attachment",
                },
                timeout=30,
            )
            result = response.json()

            if response.status_code == 200 and result.get("success"):
                print("   ✅ PASS: Successfully attached file")
                print(f"      Attachment ID: {result.get('attachment_id')}")
                print(f"      Attachment Key: {result.get('attachment_key')}")
                return True
            else:
                print(f"   ❌ FAIL: Attachment failed: {result}")
                return False
        except Exception as e:
            print(f"   ❌ FAIL: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all tests and report results."""
        print("=" * 60)
        print("Fulltext Attachment API Test Suite")
        print("=" * 60)

        # Check prerequisites
        if not self.check_zotero_running():
            print("\n❌ ERROR: Zotero is not running or API is not accessible")
            print("Please start Zotero and ensure the extension is installed")
            return False

        print("\n✅ Zotero is running and accessible")

        # Get test item
        self.get_test_item_key()
        if self.test_item_key:
            print(f"✅ Using test item: {self.test_item_key}")
        else:
            print("⚠️  WARNING: No test item found, some tests will be skipped")

        # Run tests
        results = []
        results.append(self.test_endpoint_exists())
        results.append(self.test_post_method())
        results.append(self.test_validation_missing_fields())
        results.append(self.test_file_not_found())
        results.append(self.test_invalid_item_key())
        results.append(self.test_successful_attachment())

        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)

        passed = sum(1 for r in results if r is True)
        failed = sum(1 for r in results if r is False)
        skipped = sum(1 for r in results if r is None)
        total = len(results)

        print(f"Total tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")

        if failed == 0:
            print("\n✅ All tests passed!")
            return True
        else:
            print(f"\n❌ {failed} tests failed")
            return False


def main():
    """Main test runner."""
    tester = TestFulltextAttachAPI()
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        tester.cleanup()


if __name__ == "__main__":
    main()
