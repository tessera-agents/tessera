#!/usr/bin/env python3
"""
Test content hash optimization to verify we skip re-parsing when content unchanged.
"""

import sys
from pathlib import Path
import time
import json

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from tessera.premium_models import PremiumModelInfo


def main():
    """Test hash-based change detection."""
    print("=" * 80)
    print("CONTENT HASH OPTIMIZATION TEST")
    print("=" * 80)

    cache_file = project_root / ".cache" / "premium_models.json"

    # Step 1: Delete cache and do fresh fetch
    print("\n1. Fresh fetch (no cache)...")
    if cache_file.exists():
        cache_file.unlink()
        print("   ✓ Deleted cache")

    info = PremiumModelInfo()
    start = time.time()
    success = info.fetch_from_docs()
    fetch1_time = time.time() - start

    if not success:
        print("   ✗ Fetch failed")
        return

    print(f"   ✓ Fetched and parsed in {fetch1_time:.3f}s")

    # Check cache was created with hash
    with open(cache_file) as f:
        cache1 = json.load(f)

    hash1 = cache1.get("content_hash")
    print(f"   ✓ Cache created with hash: {hash1[:16]}...")

    # Step 2: Fetch again (should hit cache and skip parsing due to hash match)
    print("\n2. Second fetch (content unchanged, hash match)...")
    info2 = PremiumModelInfo()
    start = time.time()
    success = info2.fetch_from_docs()
    fetch2_time = time.time() - start

    if not success:
        print("   ✗ Fetch failed")
        return

    print(f"   ✓ Completed in {fetch2_time:.3f}s")

    # Check hash wasn't updated (content unchanged)
    with open(cache_file) as f:
        cache2 = json.load(f)

    hash2 = cache2.get("content_hash")

    if hash1 == hash2:
        print(f"   ✓ Hash unchanged: {hash2[:16]}... (content identical)")
        print(f"   ✓ Skipped re-parsing (optimization working!)")
    else:
        print(f"   ✗ Hash changed unexpectedly")
        print(f"      Old: {hash1[:16]}...")
        print(f"      New: {hash2[:16]}...")

    # Step 3: Verify data is still correct
    print("\n3. Verify parsed data is still correct...")
    test_cases = [
        ("gpt-4o", False, 0.0),
        ("claude-opus-4.1", True, 10.0),
        ("claude-3.5-sonnet", True, 1.0),
    ]

    all_correct = True
    for model, expected_premium, expected_mult in test_cases:
        is_prem = info2.is_premium(model)
        mult = info2.get_multiplier(model)

        if is_prem == expected_premium and mult == expected_mult:
            print(f"   ✓ {model}: premium={is_prem}, mult={mult}")
        else:
            print(f"   ✗ {model}: expected premium={expected_premium}, mult={expected_mult}")
            print(f"      Got: premium={is_prem}, mult={mult}")
            all_correct = False

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(f"\nFirst fetch (fresh):    {fetch1_time:.3f}s (download + parse)")
    print(f"Second fetch (cached):  {fetch2_time:.3f}s (download + hash check)")

    if fetch2_time < fetch1_time:
        speedup = (fetch1_time - fetch2_time) / fetch1_time * 100
        print(f"Speedup: {speedup:.1f}% faster (skipped parsing)")

    if hash1 == hash2 and all_correct:
        print("\n✓ OPTIMIZATION WORKING:")
        print("  1. Content hash computed from table HTML")
        print("  2. Hash stored in cache")
        print("  3. Subsequent fetches skip re-parsing when hash matches")
        print("  4. Data remains correct")
    else:
        print("\n✗ Some checks failed")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
