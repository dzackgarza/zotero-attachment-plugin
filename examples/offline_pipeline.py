#!/usr/bin/env python3
"""
Simple Offline Pipeline Example

This script demonstrates an offline processing pipeline that:
1. Connects to your local Zotero library using `pyzotero`.
2. Finds items that have PDF attachments but no extracted fulltext notes.
3. Retrieves the PDF file path.
4. (Simulated) Extracts the text content.
5. Attaches the extracted text back to the Zotero item using `zotero-local-write-api`.

Requirements:
- pip install pyzotero requests
- pdftotext (or another CLI text extraction tool)
- The zotero-local-write-api plugin installed in Zotero
"""

import os
import sys
import json
import shutil
import tempfile
import requests
import subprocess
from pathlib import Path

try:
    from pyzotero import zotero
except ImportError:
    print("Please install required packages: pip install pyzotero requests")
    sys.exit(1)

# Configuration for the Local Write API
ZOTERO_WRITE_API_URL = "http://localhost:23119/write"
ZOTERO_ATTACH_API_URL = "http://localhost:23119/attach"

def get_local_zotero_client() -> zotero.Zotero:
    """Get authenticated Zotero client using the local API."""
    library_id = os.getenv("ZOTERO_LIBRARY_ID", "0")
    library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")

    return zotero.Zotero(
        library_id=library_id,
        library_type=library_type,
        api_key=None,
        local=True,
    )

def has_fulltext_note(client: zotero.Zotero, item_key: str) -> bool:
    """Check if item already has a fulltext note attached."""
    try:
        children = client.children(item_key)
        for child in children:
            if (
                child.get("data", {}).get("itemType") == "note"
                and "Fulltext Content" in child.get("data", {}).get("note", "")
            ):
                return True
    except Exception as e:
        print(f"Error checking children for {item_key}: {e}")
    return False

def get_pdf_path(client: zotero.Zotero, item_key: str) -> str:
    """Find the absolute path to the best PDF attachment for an item."""
    try:
        children = client.children(item_key)
        for child in children:
            data = child.get("data", {})
            if data.get("itemType") == "attachment" and data.get("contentType") == "application/pdf":
                # In a real scenario, you can locate the file on disk using the Zotero data directory
                # and item key. However, for this example, we'll demonstrate downloading it via pyzotero
                # into a temporary directory if needed.
                # Locally, it's typically at: ~/Zotero/storage/<ATTACHMENT_KEY>/<filename>
                attachment_key = data.get("key")
                filename = data.get("filename")
                zotero_data_dir = os.path.expanduser("~/Zotero")
                possible_path = os.path.join(zotero_data_dir, "storage", attachment_key, filename)
                
                if os.path.exists(possible_path):
                    return possible_path
    except Exception as e:
         print(f"Error retrieving PDF for {item_key}: {e}")
    return ""

def attach_fulltext_via_api(item_key: str, text_content: str) -> bool:
    """
    Attach extracted text as a child note using the zotero-local-write-api /write endpoint.
    """
    note_html = f"<h1>Fulltext Content</h1><p><pre>{text_content[:2000]}... (truncated)</pre></p>"
    
    payload = {
        "operation": "attach_note",
        "parent_item_key": item_key,
        "note_text": note_html,
        "title": "Fulltext Content"
    }

    try:
        response = requests.post(ZOTERO_WRITE_API_URL, json=payload, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("success", False)
    except requests.exceptions.RequestException as e:
        print(f"API Error attaching note: {e}")
        return False

def extract_text(pdf_path: str) -> str:
    """Extract text from a PDF file using pdftotext."""
    if not shutil.which("pdftotext"):
        print("Warning: pdftotext not found. Simulating extraction.")
        return "Simulated extracted text content..."
        
    try:
        # Run pdftotext to extract text to stdout
        result = subprocess.run(
            ["pdftotext", "-q", "-enc", "UTF-8", pdf_path, "-"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Failed to extract text: {e}")
        return ""

def main():
    print("Initializing offline processing pipeline...")
    
    client = get_local_zotero_client()
    
    # Example: fetch the top 20 items to process
    print("Fetching items...")
    items = client.items(limit=20)
    
    processed_count = 0
    
    for item in items:
        item_key = item.get("data", {}).get("key")
        title = item.get("data", {}).get("title", "Untitled")
        item_type = item.get("data", {}).get("itemType", "")
        
        # Skip attachments/notes, we want parent items
        if item_type in ["attachment", "note"]:
             continue
             
        print(f"\nProcessing {item_key}: {title[:50]}...")
        
        if has_fulltext_note(client, item_key):
             print("  -> Already has fulltext note. Skipping.")
             continue
             
        pdf_path = get_pdf_path(client, item_key)
        if not pdf_path:
             print("  -> No PDF attachment found.")
             continue
             
        print(f"  -> Found PDF at: {pdf_path}")
        
        print("  -> Extracting text...")
        text_content = extract_text(pdf_path)
        
        if not text_content.strip():
             print("  -> Text extraction failed or resulted in empty output.")
             continue
             
        print("  -> Attaching extracted text to Zotero...")
        success = attach_fulltext_via_api(item_key, text_content)
        
        if success:
             print("  [OK] Extracted text attached successfully!")
             processed_count += 1
        else:
             print("  [FAIL] Failed to attach text via local API.")
             
    print(f"\nPipeline complete. Processed {processed_count} new items.")

if __name__ == "__main__":
     main()
