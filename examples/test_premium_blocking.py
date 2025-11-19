#!/usr/bin/env python3
"""
Test premium model blocking functionality.

This demonstrates how the framework automatically blocks premium models
unless explicitly opted-in via allow_premium_models=True.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from tessera.config import LLMConfig


def test_free_model_allowed():
    """Test that free models work without opt-in."""
    print("\nTest 1: Free model (gpt-4) should work without opt-in...")
    try:
        config = LLMConfig(
            provider="openai",
            models=["gpt-4"],  # Legacy model, should be free
            base_url="http://localhost:4141/v1"
        )
        print("✓ Success! gpt-4 is allowed (legacy/free model)")
    except ValueError as e:
        print(f"✗ Failed: {e}")


def test_premium_model_blocked():
    """Test that premium models are blocked without opt-in."""
    print("\nTest 2: Premium model (claude-3.5-sonnet) should be blocked...")
    try:
        config = LLMConfig(
            provider="openai",
            models=["claude-3.5-sonnet"],  # Premium model
            base_url="http://localhost:4141/v1"
        )
        print("✗ Failed! Premium model was allowed without opt-in")
    except ValueError as e:
        print("✓ Success! Premium model was blocked")
        print(f"\nError message preview:")
        print(str(e)[:300] + "...")


def test_premium_model_with_optin():
    """Test that premium models work WITH opt-in."""
    print("\nTest 3: Premium model WITH opt-in should work...")
    try:
        config = LLMConfig(
            provider="openai",
            models=["claude-3.5-sonnet"],
            base_url="http://localhost:4141/v1",
            allow_premium_models=True  # Explicit opt-in
        )
        print("✓ Success! Premium model allowed with opt-in")
    except ValueError as e:
        print(f"✗ Failed: {e}")


def test_expensive_model_blocked():
    """Test that expensive models (high multiplier) are blocked."""
    print("\nTest 4: Expensive model (claude-opus-4.1, 10× multiplier) should be blocked...")
    try:
        config = LLMConfig(
            provider="openai",
            models=["claude-opus-4.1"],  # 10× multiplier!
            base_url="http://localhost:4141/v1"
        )
        print("✗ Failed! Expensive model was allowed without opt-in")
    except ValueError as e:
        print("✓ Success! Expensive model was blocked")
        if "10×" in str(e) or "EXPENSIVE" in str(e):
            print("✓ Error message correctly flags high multiplier")


def test_no_blocking_without_proxy():
    """Test that validation doesn't run without base_url."""
    print("\nTest 5: No blocking when not using Copilot proxy...")
    try:
        config = LLMConfig(
            provider="openai",
            models=["claude-3.5-sonnet"],
            # No base_url = not using Copilot proxy
        )
        print("✓ Success! No validation when base_url not set")
    except ValueError as e:
        print(f"✗ Failed: {e}")


def main():
    """Run all tests."""
    print("=" * 80)
    print("PREMIUM MODEL BLOCKING TESTS")
    print("=" * 80)

    test_free_model_allowed()
    test_premium_model_blocked()
    test_premium_model_with_optin()
    test_expensive_model_blocked()
    test_no_blocking_without_proxy()

    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
