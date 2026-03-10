#!/usr/bin/env python3
"""
Find Zotero item by BibTeX key.

This example script demonstrates how to locate a Zotero item in your local library
by searching for its Better BibTeX citation key using the standard pyzotero library.
"""

import os
import sys

try:
    from pyzotero import zotero
except ImportError:
    print("Please install pyzotero: pip install pyzotero")
    sys.exit(1)

def get_local_zotero_client() -> zotero.Zotero:
    """
    Get authenticated Zotero client using the local API.
    """
    # Use environment variables if available, otherwise assume local user library
    library_id = os.getenv("ZOTERO_LIBRARY_ID", "0")
    library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")

    return zotero.Zotero(
        library_id=library_id,
        library_type=library_type,
        api_key=None,  # Not needed for local API
        local=True,    # Force local mode
    )

def main():
    if len(sys.argv) < 2:
        print("Usage: python find_item_by_bibtex.py <bibtex_key>")
        print("Example: python find_item_by_bibtex.py Ale22")
        sys.exit(1)

    target_key = sys.argv[1]
    
    try:
        client = get_local_zotero_client()
    except Exception as e:
        print(f"Failed to connect to local Zotero API: {e}")
        print("Make sure Zotero is running and the local API is enabled.")
        sys.exit(1)

    print(f"Searching for BibTeX key: {target_key}")

    # Fetch items in batches (limit=100)
    items = client.items(limit=100)
    found = False

    def check_items(item_list):
        for item in item_list:
            data = item.get("data", {})
            # Check citation key field (where Better BibTeX keys are typically stored)
            citation_key = data.get("citationKey", "")
            if citation_key == target_key:
                print(f"\nFound item with BibTeX key '{target_key}':")
                print(f"  Item Key: {data.get('key')}")
                print(f"  Title: {data.get('title', 'No title')}")
                
                authors = ", ".join(
                    [
                        f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()
                        for c in data.get("creators", [])
                    ]
                )
                print(f"  Authors: {authors}")
                print(f"  Year: {data.get('date', 'Unknown')}")
                print(f"  Item Type: {data.get('itemType')}")
                return True
        return False

    # Check first batch
    if check_items(items):
        found = True

    if not found:
        print("Not found in first 100 items, falling back to searching all items...")
        try:
            all_items = client.everything(client.items())
            if check_items(all_items):
                found = True
        except Exception as e:
            print(f"Error fetching all items: {e}")
            
    if not found:
        print(f"\nNo item found with BibTeX key '{target_key}'")

if __name__ == "__main__":
    main()
