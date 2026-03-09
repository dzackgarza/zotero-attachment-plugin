#!/usr/bin/env python3
"""
Integration example showing the complete workflow:
1. Extract fulltext from PDF
2. Attach to Zotero item using the API
3. Verify attachment was created
"""

import os
import sys
from pathlib import Path

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent))

from scripts.canonical_pdf_extraction import extract_fulltext_from_pdf
from scripts.fulltext_attach_client import FulltextAttachClient


def demonstrate_workflow(pdf_path: str, item_key: str):
    """
    Demonstrate the complete workflow from PDF to Zotero attachment.

    Args:
        pdf_path: Path to PDF file
        item_key: Zotero item key to attach to
    """
    print("=" * 60)
    print("Fulltext Attachment Workflow Demo")
    print("=" * 60)

    # Step 1: Extract fulltext from PDF
    print(f"\n1. Extracting fulltext from: {pdf_path}")
    try:
        fulltext = extract_fulltext_from_pdf(pdf_path)
        print(f"   ✅ Extracted {len(fulltext)} characters")

        # Show sample
        sample = fulltext[:200].replace("\n", " ")
        print(f"   Sample: {sample}...")

        # Check for specific content
        if "Γrhas 19 roots" in fulltext:
            print("   ✅ Found 'Γrhas 19 roots' in text")
    except Exception as e:
        print(f"   ❌ Extraction failed: {e}")
        return False

    # Step 2: Connect to Zotero API
    print("\n2. Connecting to Zotero API...")
    client = FulltextAttachClient()

    if not client.check_connection():
        print("   ❌ Cannot connect to Zotero")
        print("   Make sure Zotero is running and the extension is installed")
        return False

    print("   ✅ Connected to Zotero API")

    # Step 3: Attach fulltext to Zotero item
    print(f"\n3. Attaching fulltext to item: {item_key}")
    try:
        result = client.attach_text(
            item_key=item_key,
            text_content=fulltext,
            title=f"Fulltext - {Path(pdf_path).stem}",
        )

        print("   ✅ Successfully attached fulltext!")
        print(f"   Attachment ID: {result['attachment_id']}")
        print(f"   Attachment Key: {result['attachment_key']}")
        print(f"   Message: {result['message']}")

    except Exception as e:
        print(f"   ❌ Attachment failed: {e}")
        return False

    # Step 4: Verify in Zotero
    print("\n4. Next steps:")
    print("   - Open Zotero and find the item")
    print("   - Look for the new attachment")
    print("   - Try searching for 'Γrhas 19 roots' in Zotero")
    print("   - The fulltext should be indexed and searchable")

    print("\n✅ Workflow completed successfully!")
    return True


def batch_processing_example():
    """Example of batch processing multiple PDFs."""
    print("\n" + "=" * 60)
    print("Batch Processing Example")
    print("=" * 60)

    # Example batch data
    papers = [
        {"pdf": "/path/to/paper1.pdf", "item_key": "ABC123"},
        {"pdf": "/path/to/paper2.pdf", "item_key": "DEF456"},
        {"pdf": "/path/to/paper3.pdf", "item_key": "GHI789"},
    ]

    client = FulltextAttachClient()

    for paper in papers:
        print(f"\nProcessing: {paper['pdf']}")
        try:
            # Extract fulltext
            fulltext = extract_fulltext_from_pdf(paper["pdf"])

            # Attach to Zotero
            client.attach_text(
                item_key=paper["item_key"],
                text_content=fulltext,
                title=f"Fulltext - {Path(paper['pdf']).stem}",
            )

            print(f"✅ Success: Attached to {paper['item_key']}")

        except Exception as e:
            print(f"❌ Failed: {e}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Demonstrate fulltext extraction and attachment workflow"
    )
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("item_key", help="Zotero item key to attach to")
    parser.add_argument(
        "--batch", action="store_true", help="Show batch processing example"
    )

    args = parser.parse_args()

    # Validate PDF exists
    if not os.path.exists(args.pdf_path):
        print(f"❌ Error: PDF not found: {args.pdf_path}")
        sys.exit(1)

    # Run workflow
    success = demonstrate_workflow(args.pdf_path, args.item_key)

    if args.batch:
        batch_processing_example()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # If no arguments, show example usage
    if len(sys.argv) == 1:
        print("Example usage:")
        print("  python integration_example.py /path/to/paper.pdf ITEM_KEY")
        print("\nFor testing with Alexeev paper:")
        print("  python integration_example.py ../../test_data/alexeev.pdf BXXECN89")
        sys.exit(1)

    main()
