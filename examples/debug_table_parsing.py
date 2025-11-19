#!/usr/bin/env python3
"""
Debug the table parsing to see exactly what's being extracted.
"""

import re
import requests

DOCS_URL = "https://docs.github.com/en/copilot/concepts/billing/copilot-requests"


def main():
    """Debug the table parsing."""
    print("=" * 80)
    print("DEBUGGING TABLE PARSING")
    print("=" * 80)

    print(f"\nFetching: {DOCS_URL}")
    response = requests.get(DOCS_URL, timeout=10)
    html = response.text

    # Step 1: Find the model-multipliers section
    print("\n1. Looking for model-multipliers table...")
    table_pattern = r'<h2 id="model-multipliers".*?<table>(.*?)</table>'
    table_match = re.search(table_pattern, html, re.DOTALL)

    if not table_match:
        print("✗ Table not found!")
        return

    print("✓ Table found!")
    table_html = table_match.group(1)
    print(f"   Table HTML length: {len(table_html)} chars")

    # Step 2: Extract table rows
    print("\n2. Extracting table rows...")
    row_pattern = r'<tr><th scope="row">(.*?)</th><td>(.*?)</td><td>(.*?)</td></tr>'
    rows = re.findall(row_pattern, table_html, re.DOTALL)

    print(f"   Found {len(rows)} rows")

    # Step 3: Parse each row
    print("\n3. Parsing rows:")
    print("=" * 80)

    for i, (model_name, mult_paid, mult_free) in enumerate(rows, 1):
        model_clean = model_name.strip()
        mult_paid_clean = mult_paid.strip()
        mult_free_clean = mult_free.strip()

        print(f"\nRow {i}:")
        print(f"  Raw model:     '{model_name}'")
        print(f"  Clean model:   '{model_clean}'")
        print(f"  Multiplier (paid):  '{mult_paid_clean}'")
        print(f"  Multiplier (free):  '{mult_free_clean}'")

        # Try to normalize
        model_lower = model_clean.lower()
        print(f"  Lowercase:     '{model_lower}'")

        # Check if it can be converted to float
        try:
            mult_value = float(mult_paid_clean)
            print(f"  Parsed multiplier: {mult_value}")
        except ValueError as e:
            print(f"  ✗ Cannot parse multiplier: {e}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
