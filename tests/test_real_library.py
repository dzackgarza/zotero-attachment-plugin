#!/usr/bin/env python3
"""
Real Library Integration Tests
==============================

These tests use ACTUAL hardcoded values from the user's real Zotero library.
They are separated from the general tests to make it clear they have specific dependencies.

WARNING: These tests will ONLY work on the original developer's system with their
specific Zotero library containing these exact items.

For general testing, use test_tdd_integration.py or test_api_endpoint.py
"""

import os
import sys
import tempfile

import requests

# Test configuration
ZOTERO_API_BASE = "http://localhost:23119"
FULLTEXT_ENDPOINT = f"{ZOTERO_API_BASE}/fulltext-attach"

# REAL LIBRARY VALUES - These are actual items in the developer's Zotero
ALEXEEV_ITEM_KEY = "BXXECN89"  # Alexeev paper with "Γrhas 19 roots"
# Add more real item keys as needed for specific tests


class TestRealLibrary:
    """Tests using real hardcoded library items."""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="zotero_real_test_")

    def check_prerequisites(self):
        """Check that Zotero is running and extension is installed."""
        # Check Zotero
        try:
            response = requests.get(f"{ZOTERO_API_BASE}/api/config", timeout=5)
            if response.status_code != 200:
                print("❌ Zotero is not running")
                return False
        except Exception:
            print("❌ Cannot connect to Zotero")
            return False

        # Check extension endpoint
        try:
            response = requests.post(FULLTEXT_ENDPOINT, json={}, timeout=5)
            if response.status_code == 404:
                print("❌ Extension not installed")
                return False
        except Exception:
            pass

        return True

    def test_alexeev_paper_attachment(self):
        """Test attaching fulltext to the Alexeev paper specifically."""
        print("\nTest: Alexeev Paper Attachment (BXXECN89)")
        print("-" * 50)

        # Create fulltext with the specific content we know is in this paper
        alexeev_content = """
Extracted from Alexeev paper:

The main result states that Γrhas 19 roots.

This is a test of mathematical content preservation
including special symbols and expressions.
"""

        test_file = os.path.join(self.temp_dir, "alexeev_fulltext.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(alexeev_content)

        try:
            response = requests.post(
                FULLTEXT_ENDPOINT,
                json={
                    "item_key": ALEXEEV_ITEM_KEY,
                    "file_path": test_file,
                    "title": "Alexeev Fulltext (Real Test)",
                },
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print("✅ Successfully attached to Alexeev paper")
                    print(f"   Attachment ID: {result.get('attachment_id')}")
                    print(f"   Attachment Key: {result.get('attachment_key')}")

                    # Store for verification
                    self.last_alexeev_attachment = result.get("attachment_key")
                    return True

            print(f"❌ Failed to attach: {response.status_code}")
            print(f"   Response: {response.json()}")
            return False

        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    def test_search_for_gamma_roots(self):
        """Test that we can search for 'Γrhas 19 roots' in Zotero."""
        print("\nTest: Search for 'Γrhas 19 roots'")
        print("-" * 50)

        search_query = "Γrhas 19 roots"

        try:
            # Use Zotero's search API
            response = requests.get(
                f"{ZOTERO_API_BASE}/api/library/items",
                params={"q": search_query},
                timeout=10,
            )

            if response.status_code == 200:
                results = response.json()

                # Check if Alexeev paper is in results
                found_alexeev = any(
                    item.get("key") == ALEXEEV_ITEM_KEY for item in results
                )

                if found_alexeev:
                    print(f"✅ Found Alexeev paper when searching for '{search_query}'")
                    return True
                else:
                    print("❌ Alexeev paper not found in search results")
                    print(f"   Found {len(results)} other items")
                    return False
            else:
                print(f"❌ Search failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error during search: {e}")
            return False

    def test_specific_collection_item(self):
        """Test with items from specific collections if you have them."""
        print("\nTest: Specific Collection Items")
        print("-" * 50)

        # Example: If you have specific items in collections
        # MACHINE_LEARNING_ITEM = "ABC123"
        # MATHEMATICS_ITEM = "DEF456"

        print("⚠️  Add your own specific item keys here")
        return None

    def test_large_textbook_attachment(self):
        """Test attaching a large file (simulating textbook)."""
        print("\nTest: Large File Attachment (Textbook Simulation)")
        print("-" * 50)

        # Create a large test file (10MB)
        large_content = "Chapter 1: Introduction\n\n" + ("x" * 1024 * 1024 * 10)
        test_file = os.path.join(self.temp_dir, "large_textbook.txt")

        print("Creating 10MB test file...")
        with open(test_file, "w") as f:
            f.write(large_content)

        try:
            response = requests.post(
                FULLTEXT_ENDPOINT,
                json={
                    "item_key": ALEXEEV_ITEM_KEY,
                    "file_path": test_file,
                    "title": "Large Textbook Test",
                },
                timeout=60,  # Longer timeout for large file
            )

            if response.status_code == 200 and response.json().get("success"):
                print("✅ Successfully attached large file (10MB)")
                return True
            else:
                print(f"❌ Failed to attach large file: {response.json()}")
                return False

        except Exception as e:
            print(f"❌ Error with large file: {e}")
            return False

    def cleanup(self):
        """Clean up test files."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil

            shutil.rmtree(self.temp_dir)

    def run_all_tests(self):
        """Run all real library tests."""
        print("=" * 60)
        print("Real Library Integration Tests")
        print("Using actual Zotero library items")
        print("=" * 60)

        if not self.check_prerequisites():
            print("\n❌ Prerequisites not met. Stopping tests.")
            return False

        print("\n✅ Prerequisites checked - Zotero running, extension installed")

        # Run tests
        tests = [
            self.test_alexeev_paper_attachment,
            self.test_search_for_gamma_roots,
            self.test_specific_collection_item,
            self.test_large_textbook_attachment,
        ]

        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                results.append(False)

        # Summary
        print("\n" + "=" * 60)
        print("Real Library Test Summary")
        print("=" * 60)

        passed = sum(1 for r in results if r is True)
        failed = sum(1 for r in results if r is False)
        skipped = sum(1 for r in results if r is None)

        print(f"Total: {len(results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")

        return failed == 0


def main():
    """Main test runner."""
    print("Starting Real Library Tests...")
    print("These tests use REAL items from the developer's Zotero library\n")

    tester = TestRealLibrary()
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        tester.cleanup()


if __name__ == "__main__":
    main()
