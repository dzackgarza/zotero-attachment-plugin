#!/usr/bin/env python3
"""
Client script for the Fulltext Attachment API.
This now imports from the refactored module in src/zotero_mcp/plugin_interface.py
"""

import sys
from pathlib import Path

# Add src to path to import the refactored module
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from zotero_mcp.plugin_interface import FulltextAttachClient  # noqa: E402


def main():
    """Example usage of the client."""
    client = FulltextAttachClient()

    # Check connection
    if not client.check_connection():
        print("❌ Error: Cannot connect to Zotero. Is it running?")
        print("   Make sure Zotero is open and the extension is installed.")
        return

    print("✅ Connected to Zotero")

    # Example 1: Attach a file
    try:
        # You would replace these with actual values
        item_key = "BXXECN89"  # Replace with actual item key
        file_path = "/tmp/example.txt"  # Replace with actual file

        # Create example file
        with open(file_path, "w") as f:
            f.write("Example fulltext content\nΓrhas 19 roots")

        result = client.attach_file(
            item_key=item_key, file_path=file_path, title="Example Fulltext"
        )

        print("\n✅ Successfully attached file:")
        print(f"   Attachment ID: {result['attachment_id']}")
        print(f"   Attachment Key: {result['attachment_key']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")

    # Example 2: Attach text content directly
    try:
        text_content = """
        This is example fulltext content.
        It contains mathematical expressions like Γrhas 19 roots.
        And multiple lines of text.
        """

        result = client.attach_text(
            item_key=item_key, text_content=text_content, title="Direct Text Attachment"
        )

        print("\n✅ Successfully attached text content:")
        print(f"   Attachment ID: {result['attachment_id']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")

    # Example 3: Batch attachment
    try:
        attachments = [
            {
                "item_key": "ABC123",
                "file_path": "/tmp/file1.txt",
                "title": "Document 1",
            },
            {
                "item_key": "DEF456",
                "file_path": "/tmp/file2.txt",
                "title": "Document 2",
            },
        ]

        # Create example files
        for att in attachments:
            with open(att["file_path"], "w") as f:
                f.write(f"Content for {att['title']}")

        results = client.batch_attach_files(attachments)

        print("\n✅ Batch attachment results:")
        for result in results:
            if result["success"]:
                print(f"   ✅ {result['item_key']}: Success")
            else:
                print(f"   ❌ {result['item_key']}: {result['error']}")

    except Exception as e:
        print(f"\n❌ Error in batch: {e}")


if __name__ == "__main__":
    main()
