#!/usr/bin/env python3
"""
Simple test for the event discovery API endpoint.
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wave_v1.settings")
import django

django.setup()

from socialGraphManagement.recommendations.event.event import (
    get_personalized_event_discovery,
)


def test_discovery_function():
    """Test the discovery function directly."""

    print("=== Testing Event Discovery Function ===\n")

    try:
        # Test with a sample user ID (you may need to replace this with a real user ID)
        test_user_id = "test-user-123"

        print(f"Testing with user ID: {test_user_id}")

        # Test without college
        results = get_personalized_event_discovery(test_user_id, None, 10)
        print(f"Results without college: {len(results)} events")

        # Test with college
        results_with_college = get_personalized_event_discovery(
            test_user_id, "Test College", 10
        )
        print(f"Results with college: {len(results_with_college)} events")

        print("✓ Discovery function works")

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_discovery_function()
