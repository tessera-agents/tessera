#!/usr/bin/env python3
"""
Debug the HTML parsing to see what's actually being extracted.
"""

import re
import requests

DOCS_URL = "https://docs.github.com/en/copilot/concepts/billing/copilot-requests"


def main():
    """Debug the parsing logic."""
    print("=" * 80)
    print("DEBUGGING PREMIUM MODEL PARSING")
    print("=" * 80)

    print(f"\nFetching: {DOCS_URL}")
    response = requests.get(DOCS_URL, timeout=10)

    if response.status_code != 200:
        print(f"Failed to fetch: {response.status_code}")
        return

    html = response.text
    print(f"✓ Fetched {len(html)} bytes")

    # Parse premium models with multipliers
    print("\n" + "=" * 80)
    print("PARSING PREMIUM MODELS (looking for pattern: 'Model Name: X×')")
    print("=" * 80)

    premium_pattern = r'([A-Za-z0-9\s\.\-]+):\s*(\d+(?:\.\d+)?)×'
    matches = re.findall(premium_pattern, html)

    print(f"\nFound {len(matches)} matches:")
    for i, (model_name, multiplier) in enumerate(matches, 1):
        print(f"{i:2}. '{model_name}' → {multiplier}×")

    # Parse free models
    print("\n" + "=" * 80)
    print("PARSING FREE MODELS (looking for 'unlimited' or 'don't consume')")
    print("=" * 80)

    free_pattern = r'([A-Za-z0-9\.\-\s]+)\s+(?:are|is)\s+(?:unlimited|don\'t\s+consume)'
    free_matches = re.findall(free_pattern, html, re.IGNORECASE)

    print(f"\nFound {len(free_matches)} matches:")
    for i, model_name in enumerate(free_matches, 1):
        print(f"{i:2}. '{model_name}'")

    # Save a snippet of the HTML for manual inspection
    print("\n" + "=" * 80)
    print("SAMPLE HTML SNIPPETS (searching for 'premium' and 'multiplier')")
    print("=" * 80)

    # Find lines containing relevant keywords
    lines = html.split('\n')
    relevant_lines = []
    for i, line in enumerate(lines):
        lower = line.lower()
        if any(keyword in lower for keyword in ['premium', 'multiplier', 'claude', 'gpt-5', 'unlimited', 'request']):
            relevant_lines.append((i, line.strip()))

    # Show some samples
    print(f"\nShowing first 20 relevant lines (out of {len(relevant_lines)} total):")
    for i, (line_num, line) in enumerate(relevant_lines[:20]):
        # Truncate long lines
        display = line[:150] + "..." if len(line) > 150 else line
        print(f"{line_num:5}: {display}")

    # Check if the patterns we're looking for actually exist
    print("\n" + "=" * 80)
    print("PATTERN VERIFICATION")
    print("=" * 80)

    # Look for explicit model names and multipliers in the HTML
    test_patterns = [
        (r'claude-opus.*?10', 'Claude Opus with 10× multiplier'),
        (r'claude.*?sonnet.*?1×', 'Claude Sonnet with 1× multiplier'),
        (r'gpt-4o.*?unlimited', 'GPT-4o unlimited'),
        (r'gpt-5-mini.*?unlimited', 'GPT-5-mini unlimited'),
    ]

    for pattern, description in test_patterns:
        if re.search(pattern, html, re.IGNORECASE):
            print(f"✓ Found: {description}")
        else:
            print(f"✗ Not found: {description}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
