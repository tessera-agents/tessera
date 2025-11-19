#!/usr/bin/env python3
"""
Verify that premium model information is being parsed from GitHub docs,
not just using hardcoded fallbacks.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from tessera.premium_models import get_premium_info


def main():
    """Test that parsing from GitHub docs works."""
    print("=" * 80)
    print("VERIFYING PREMIUM MODEL PARSING FROM GITHUB DOCS")
    print("=" * 80)

    info = get_premium_info()

    # Force fetch from docs (bypass cache)
    print("\n1. Fetching from GitHub documentation...")
    print(f"   URL: https://docs.github.com/en/copilot/concepts/billing/copilot-requests")

    success = info.fetch_from_docs()

    if success:
        print("   ✓ Successfully fetched and parsed!")
    else:
        print("   ✗ Failed to fetch - using fallback data")
        return

    # Show what was parsed
    print("\n2. Premium models found (with multipliers):")
    print("=" * 80)
    premium = info.get_all_premium_models()
    if premium:
        for model, multiplier in sorted(premium.items(), key=lambda x: x[1]):
            if multiplier < 1.0:
                print(f"   • {model:30} {multiplier}× (discounted)")
            elif multiplier == 1.0:
                print(f"   • {model:30} {multiplier}×")
            else:
                print(f"   • {model:30} {int(multiplier)}× (EXPENSIVE!)")
    else:
        print("   No premium models found (parsing may have failed)")

    print(f"\n   Total premium models: {len(premium)}")

    # Show free models
    print("\n3. Free models found (unlimited):")
    print("=" * 80)
    free = info.get_all_free_models()
    if free:
        for model in sorted(free):
            print(f"   • {model}")
    else:
        print("   No free models found (parsing may have failed)")

    print(f"\n   Total free models: {len(free)}")

    # Check if we're using hardcoded values
    print("\n4. Verification:")
    print("=" * 80)

    # Known hardcoded values from the fallback
    hardcoded_premium = {
        "claude-haiku-4.5": 0.33,
        "grok-code-fast-1": 0.25,
        "claude-3.5-sonnet": 1.0,
        "claude-sonnet-4": 1.0,
        "claude-sonnet-4.5": 1.0,
        "gemini-2.5-pro": 1.0,
        "gpt-5": 1.0,
        "gpt-5-codex": 1.0,
        "claude-opus-4.1": 10.0,
    }

    hardcoded_free = {"gpt-5-mini", "gpt-4.1", "gpt-4o"}

    # Check if parsed data differs from hardcoded
    if premium == hardcoded_premium and free == hardcoded_free:
        print("   ⚠️  WARNING: Data matches hardcoded fallback exactly!")
        print("   This suggests parsing may not be working.")
    else:
        print("   ✓ Data differs from hardcoded fallback")
        print("   ✓ Parsing appears to be working correctly")

        if len(premium) > len(hardcoded_premium):
            print(f"   ✓ Found {len(premium) - len(hardcoded_premium)} more premium models than hardcoded")
        if len(free) > len(hardcoded_free):
            print(f"   ✓ Found {len(free) - len(hardcoded_free)} more free models than hardcoded")

    # Test specific model lookups
    print("\n5. Testing specific model lookups:")
    print("=" * 80)
    test_models = [
        ("gpt-4o", False, 0.0),  # Free
        ("claude-3.5-sonnet", True, 1.0),  # Premium
        ("claude-opus-4.1", True, 10.0),  # Expensive
    ]

    for model, expected_premium, expected_mult in test_models:
        is_prem = info.is_premium(model)
        mult = info.get_multiplier(model)
        status = "✓" if is_prem == expected_premium and mult == expected_mult else "✗"
        premium_str = "PREMIUM" if is_prem else "FREE"
        print(f"   {status} {model:30} {premium_str:10} {mult}×")

    print("\n" + "=" * 80)
    print("Verification complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
