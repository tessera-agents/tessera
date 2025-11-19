#!/usr/bin/env python3
"""
Check what model information is available from copilot-api endpoints.
"""

import json
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from tessera.copilot_proxy import CopilotProxyManager
import requests


def main():
    """Check available endpoints and model information."""
    print("Starting copilot-api proxy...")

    with CopilotProxyManager(rate_limit=10, use_wait=True, verbose=False) as proxy:
        base_url = proxy.get_base_url()

        print(f"\nQuerying {base_url}/models")
        print("=" * 80)

        try:
            response = requests.get(f"{base_url}/models", timeout=10)
            print(f"Status: {response.status_code}\n")

            if response.status_code == 200:
                data = response.json()
                print(json.dumps(data, indent=2))

                # Check if there's any premium/multiplier information
                if "data" in data:
                    print("\n" + "=" * 80)
                    print("MODEL DETAILS:")
                    print("=" * 80)
                    for model in data["data"]:
                        print(f"\nModel: {model.get('id')}")
                        print(f"  Object: {model.get('object')}")
                        print(f"  Created: {model.get('created')}")
                        print(f"  Owned by: {model.get('owned_by')}")

                        # Check for any additional metadata
                        for key, value in model.items():
                            if key not in ['id', 'object', 'created', 'owned_by']:
                                print(f"  {key}: {value}")
            else:
                print(f"Error: {response.text}")

        except Exception as e:
            print(f"Error: {e}")

        # Try other potential endpoints
        print("\n" + "=" * 80)
        print("Checking other endpoints...")
        print("=" * 80)

        endpoints = [
            "/usage",
            "/token",
            "/v1/models",
            "/"
        ]

        for endpoint in endpoints:
            url = f"http://localhost:4141{endpoint}"
            try:
                response = requests.get(url, timeout=5)
                print(f"\n{endpoint}: {response.status_code}")
                if response.status_code == 200:
                    try:
                        data = response.json()
                        # Check for premium/multiplier keys
                        if any(key in str(data).lower() for key in ['premium', 'multiplier', 'quota', 'limit']):
                            print(json.dumps(data, indent=2))
                    except:
                        print(f"  (Non-JSON response: {response.text[:100]}...)")
            except Exception as e:
                print(f"  Error: {e}")


if __name__ == "__main__":
    main()
