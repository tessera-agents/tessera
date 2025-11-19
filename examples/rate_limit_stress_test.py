#!/usr/bin/env python3
"""
Rate limit stress test for GitHub Copilot proxy.

This script tests the copilot-api proxy with aggressive rate limiting to:
1. Monitor for 429 errors and rate limit behavior
2. Check /usage and /token endpoints for limit information
3. Validate logging capabilities for error detection
4. Evaluate whether use_wait should always be enabled

Usage:
    python tests/examples/rate_limit_stress_test.py
"""

import time
import sys
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")

# Add src to path for imports
sys.path.insert(0, str(project_root / "src"))

from tessera.copilot_proxy import CopilotProxyManager
from tessera.config import LLMConfig
from tessera.llm import LLMProvider

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('.cache/rate_limit_test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class TestMetrics:
    """Track test metrics and results."""

    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    # Request counters
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_errors: int = 0  # 429 errors
    other_errors: int = 0

    # Endpoint monitoring
    usage_endpoint_checks: int = 0
    token_endpoint_checks: int = 0
    usage_data: List[Dict[str, Any]] = field(default_factory=list)
    token_data: List[Dict[str, Any]] = field(default_factory=list)

    # Response timing
    response_times: List[float] = field(default_factory=list)

    # Error details
    error_details: List[Dict[str, Any]] = field(default_factory=list)

    def add_response_time(self, response_time: float):
        """Add a response time measurement."""
        self.response_times.append(response_time)

    def add_error(self, error_type: str, status_code: Optional[int], details: str):
        """Record error details."""
        self.error_details.append({
            'timestamp': datetime.now().isoformat(),
            'type': error_type,
            'status_code': status_code,
            'details': details
        })

    def get_avg_response_time(self) -> float:
        """Calculate average response time."""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)

    def get_duration_seconds(self) -> float:
        """Get test duration in seconds."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    def summary(self) -> Dict[str, Any]:
        """Generate test summary."""
        return {
            'duration_seconds': self.get_duration_seconds(),
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'rate_limit_errors_429': self.rate_limit_errors,
            'other_errors': self.other_errors,
            'success_rate': (self.successful_requests / max(self.total_requests, 1)) * 100,
            'avg_response_time_ms': self.get_avg_response_time() * 1000,
            'usage_endpoint_checks': self.usage_endpoint_checks,
            'token_endpoint_checks': self.token_endpoint_checks,
            'error_details': self.error_details
        }


class RateLimitStressTester:
    """Stress test the Copilot proxy with aggressive rate limiting."""

    def __init__(
        self,
        rate_limit: int = 10,
        use_wait: bool = True,
        port: Optional[int] = None,
        verbose: bool = True,
        test_duration_minutes: int = 5,
        request_interval: int = 12
    ):
        """
        Initialize the stress tester.

        Args:
            rate_limit: Rate limit in seconds (default: 10s - aggressive)
            use_wait: Whether to use wait mode (default: True)
            port: Proxy port (default: None, uses copilot-api default 4141)
            verbose: Enable verbose logging (default: True)
            test_duration_minutes: How long to run the test (default: 5 minutes)
            request_interval: Seconds between requests (default: 12s to stress 10s limit)
        """
        self.rate_limit = rate_limit
        self.use_wait = use_wait
        self.port = port
        self.verbose = verbose
        self.test_duration = timedelta(minutes=test_duration_minutes)
        self.request_interval = request_interval
        actual_port = port if port is not None else 4141
        self.base_url = f"http://localhost:{actual_port}"

        self.proxy_manager: Optional[CopilotProxyManager] = None
        self.metrics = TestMetrics()

        logger.info("=" * 80)
        logger.info("Rate Limit Stress Test Configuration")
        logger.info("=" * 80)
        logger.info(f"Rate limit: {rate_limit}s")
        logger.info(f"Use wait mode: {use_wait}")
        logger.info(f"Port: {port if port is not None else '4141 (default)'}")
        logger.info(f"Verbose: {verbose}")
        logger.info(f"Test duration: {test_duration_minutes} minutes")
        logger.info(f"Request interval: {request_interval}s")
        logger.info(f"Target requests per minute: {60 / request_interval:.1f}")
        logger.info("=" * 80)

    def start_proxy(self) -> bool:
        """Start the Copilot proxy with test configuration."""
        try:
            logger.info("Starting Copilot proxy...")
            self.proxy_manager = CopilotProxyManager(
                rate_limit=self.rate_limit,
                use_wait=self.use_wait,
                port=self.port,
                verbose=self.verbose
            )

            if not self.proxy_manager.start():
                logger.error("Failed to start proxy")
                return False

            # Wait for proxy to be ready
            logger.info("Waiting for proxy to be ready...")
            time.sleep(5)

            # Verify proxy is responding
            try:
                response = requests.get(f"{self.base_url}/v1/models", timeout=10)
                if response.status_code == 200:
                    logger.info("✓ Proxy is ready and responding")
                    return True
                else:
                    logger.error(f"Proxy returned unexpected status: {response.status_code}")
                    return False
            except Exception as e:
                logger.error(f"Proxy health check failed: {e}")
                return False

        except Exception as e:
            logger.error(f"Failed to start proxy: {e}")
            return False

    def stop_proxy(self):
        """Stop the Copilot proxy."""
        if self.proxy_manager:
            logger.info("Stopping Copilot proxy...")
            self.proxy_manager.stop()
            logger.info("✓ Proxy stopped")

    def check_usage_endpoint(self) -> Optional[Dict[str, Any]]:
        """Check the /usage endpoint for usage statistics."""
        try:
            logger.info("Checking /usage endpoint...")
            response = requests.get(f"{self.base_url}/usage", timeout=10)

            self.metrics.usage_endpoint_checks += 1

            logger.info(f"  Status code: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info(f"  Response: {json.dumps(data, indent=2)}")
                    self.metrics.usage_data.append({
                        'timestamp': datetime.now().isoformat(),
                        'data': data
                    })
                    return data
                except json.JSONDecodeError:
                    logger.warning(f"  Non-JSON response: {response.text[:200]}")
                    return {'raw': response.text}
            else:
                logger.warning(f"  Failed to get usage data: {response.status_code}")
                logger.warning(f"  Response: {response.text[:200]}")
                return None

        except requests.exceptions.Timeout:
            logger.error("  /usage endpoint timed out")
            return None
        except Exception as e:
            logger.error(f"  Error checking /usage endpoint: {e}")
            return None

    def check_token_endpoint(self) -> Optional[Dict[str, Any]]:
        """Check the /token endpoint for token information."""
        try:
            logger.info("Checking /token endpoint...")
            response = requests.get(f"{self.base_url}/token", timeout=10)

            self.metrics.token_endpoint_checks += 1

            logger.info(f"  Status code: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    # Redact sensitive token data in logs
                    safe_data = {k: (v if k != 'token' else '***REDACTED***')
                                for k, v in data.items()}
                    logger.info(f"  Response: {json.dumps(safe_data, indent=2)}")
                    self.metrics.token_data.append({
                        'timestamp': datetime.now().isoformat(),
                        'data': data
                    })
                    return data
                except json.JSONDecodeError:
                    logger.warning(f"  Non-JSON response: {response.text[:200]}")
                    return {'raw': response.text}
            else:
                logger.warning(f"  Failed to get token data: {response.status_code}")
                logger.warning(f"  Response: {response.text[:200]}")
                return None

        except requests.exceptions.Timeout:
            logger.error("  /token endpoint timed out")
            return None
        except Exception as e:
            logger.error(f"  Error checking /token endpoint: {e}")
            return None

    def make_test_request(self, request_num: int) -> bool:
        """
        Make a test request to the LLM endpoint.

        Args:
            request_num: Request number for logging

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Request #{request_num}: Sending test completion request...")

        self.metrics.total_requests += 1
        start_time = time.time()

        try:
            # Create LLM config pointing to the proxy
            config = LLMConfig(
                provider="openai",
                api_key="dummy-key",  # Proxy doesn't validate this
                models=["gpt-4"],  # Use models list instead of model
                temperature=0.7,
                base_url=f"{self.base_url}/v1",
                timeout=30.0
            )

            # Create LLM instance
            llm = LLMProvider.create(config)

            # Make a simple request
            messages = [
                {"role": "user", "content": f"Test request #{request_num}: What is 2+2?"}
            ]

            try:
                response = llm.invoke(messages)
                response_time = time.time() - start_time

                self.metrics.add_response_time(response_time)
                self.metrics.successful_requests += 1

                logger.info(f"  ✓ Success in {response_time*1000:.0f}ms")
                logger.info(f"  Response: {response.content[:100]}...")
                return True

            except Exception as e:
                response_time = time.time() - start_time
                error_str = str(e)

                # Check for 429 rate limit error
                if '429' in error_str or 'rate limit' in error_str.lower():
                    self.metrics.rate_limit_errors += 1
                    self.metrics.failed_requests += 1
                    logger.error(f"  ✗ RATE LIMIT ERROR (429) after {response_time*1000:.0f}ms")
                    logger.error(f"  Details: {error_str}")
                    self.metrics.add_error('rate_limit', 429, error_str)
                else:
                    self.metrics.other_errors += 1
                    self.metrics.failed_requests += 1
                    logger.error(f"  ✗ Request failed after {response_time*1000:.0f}ms")
                    logger.error(f"  Error: {error_str}")
                    self.metrics.add_error('other', None, error_str)

                return False

        except Exception as e:
            response_time = time.time() - start_time
            self.metrics.failed_requests += 1
            self.metrics.other_errors += 1
            logger.error(f"  ✗ Setup error after {response_time*1000:.0f}ms: {e}")
            self.metrics.add_error('setup', None, str(e))
            return False

    def run_test(self):
        """Run the complete stress test."""
        logger.info("\n" + "=" * 80)
        logger.info("STARTING RATE LIMIT STRESS TEST")
        logger.info("=" * 80 + "\n")

        # Start proxy
        if not self.start_proxy():
            logger.error("Failed to start proxy. Aborting test.")
            return

        try:
            # Initial endpoint checks
            logger.info("\n" + "-" * 80)
            logger.info("Initial Endpoint Checks")
            logger.info("-" * 80)
            self.check_usage_endpoint()
            self.check_token_endpoint()
            logger.info("-" * 80 + "\n")

            # Run timed test
            end_time = datetime.now() + self.test_duration
            request_num = 0

            logger.info(f"Starting request loop (will run until {end_time.strftime('%H:%M:%S')})...")
            logger.info("")

            while datetime.now() < end_time:
                request_num += 1

                # Make test request
                self.make_test_request(request_num)

                # Check endpoints periodically (every 5 requests)
                if request_num % 5 == 0:
                    logger.info("\n" + "-" * 80)
                    logger.info("Periodic Endpoint Check")
                    logger.info("-" * 80)
                    self.check_usage_endpoint()
                    self.check_token_endpoint()
                    logger.info("-" * 80 + "\n")

                # Wait before next request
                remaining_time = (end_time - datetime.now()).total_seconds()
                if remaining_time <= 0:
                    break

                wait_time = min(self.request_interval, remaining_time)
                logger.info(f"Waiting {wait_time:.1f}s before next request...\n")
                time.sleep(wait_time)

            # Final endpoint checks
            logger.info("\n" + "-" * 80)
            logger.info("Final Endpoint Checks")
            logger.info("-" * 80)
            self.check_usage_endpoint()
            self.check_token_endpoint()
            logger.info("-" * 80 + "\n")

        finally:
            # Always stop proxy
            self.stop_proxy()
            self.metrics.end_time = datetime.now()

    def print_summary(self):
        """Print test summary and recommendations."""
        summary = self.metrics.summary()

        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Duration: {summary['duration_seconds']:.1f}s ({summary['duration_seconds']/60:.1f} minutes)")
        logger.info(f"Total requests: {summary['total_requests']}")
        logger.info(f"Successful: {summary['successful_requests']}")
        logger.info(f"Failed: {summary['failed_requests']}")
        logger.info(f"Success rate: {summary['success_rate']:.1f}%")
        logger.info("")
        logger.info("Error Breakdown:")
        logger.info(f"  429 Rate Limit Errors: {summary['rate_limit_errors_429']}")
        logger.info(f"  Other Errors: {summary['other_errors']}")
        logger.info("")
        logger.info(f"Average response time: {summary['avg_response_time_ms']:.0f}ms")
        logger.info("")
        logger.info("Endpoint Monitoring:")
        logger.info(f"  /usage checks: {summary['usage_endpoint_checks']}")
        logger.info(f"  /token checks: {summary['token_endpoint_checks']}")
        logger.info("=" * 80)

        # Print recommendations
        logger.info("\n" + "=" * 80)
        logger.info("RECOMMENDATIONS")
        logger.info("=" * 80)

        # Analyze results
        if summary['rate_limit_errors_429'] > 0:
            logger.warning(f"⚠ Detected {summary['rate_limit_errors_429']} rate limit errors (429)")
            logger.warning(f"⚠ This indicates the {self.rate_limit}s rate limit is being enforced")
            if not self.use_wait:
                logger.warning("⚠ Consider enabling use_wait=True to queue requests instead of failing")
        else:
            logger.info("✓ No rate limit errors detected")
            if self.use_wait:
                logger.info("✓ use_wait=True is working correctly - requests are being queued")

        if summary['other_errors'] > 0:
            logger.warning(f"⚠ {summary['other_errors']} non-rate-limit errors occurred")
            logger.warning("⚠ Review error details above for debugging")

        # use_wait recommendation
        logger.info("")
        logger.info("use_wait Configuration:")
        if self.use_wait:
            logger.info("✓ Current setting: use_wait=True")
            if summary['rate_limit_errors_429'] == 0 and summary['successful_requests'] > 0:
                logger.info("✓ RECOMMENDATION: Keep use_wait=True (ALWAYS enabled)")
                logger.info("  Reason: Successfully queued requests without 429 errors")
            else:
                logger.info("! RECOMMENDATION: Keep use_wait=True but investigate errors")
        else:
            logger.info("✗ Current setting: use_wait=False")
            logger.info("✗ RECOMMENDATION: Change to use_wait=True (ALWAYS enabled)")
            logger.info("  Reason: Prevents 429 errors by queuing requests")

        logger.info("")
        logger.info("Rate Limit Configuration:")
        logger.info(f"  Current rate_limit: {self.rate_limit}s")
        logger.info(f"  Recommended rate_limit: 60s (based on GitHub Copilot usage patterns)")
        logger.info("  Reason: Balances request throughput with GitHub's rate limits")

        logger.info("=" * 80)

        # Save detailed results
        results_file = Path('.cache/rate_limit_test_results.json')
        results_file.parent.mkdir(parents=True, exist_ok=True)

        with open(results_file, 'w') as f:
            json.dump({
                'config': {
                    'rate_limit': self.rate_limit,
                    'use_wait': self.use_wait,
                    'port': self.port if self.port is not None else 4141,
                    'verbose': self.verbose,
                    'test_duration_minutes': self.test_duration.total_seconds() / 60,
                    'request_interval': self.request_interval
                },
                'summary': summary,
                'usage_data': self.metrics.usage_data,
                'token_data': self.metrics.token_data
            }, f, indent=2)

        logger.info(f"\nDetailed results saved to: {results_file}")
        logger.info(f"Detailed logs saved to: .cache/rate_limit_test.log")


def main():
    """Main entry point."""
    tester = RateLimitStressTester(
        rate_limit=10,  # Aggressive 10s limit
        use_wait=True,  # Test with wait enabled
        port=None,  # Use copilot-api default 4141
        verbose=True,  # Enable verbose logging for better debugging
        test_duration_minutes=5,  # 5 minute test
        request_interval=12  # Request every 12s to stress the 10s limit
    )

    try:
        tester.run_test()
        tester.print_summary()
    except KeyboardInterrupt:
        logger.warning("\n\nTest interrupted by user")
        tester.stop_proxy()
        tester.metrics.end_time = datetime.now()
        tester.print_summary()
    except Exception as e:
        logger.error(f"\n\nTest failed with error: {e}", exc_info=True)
        tester.stop_proxy()


if __name__ == "__main__":
    main()
