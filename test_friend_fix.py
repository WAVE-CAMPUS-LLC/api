#!/usr/bin/env python3
"""
Test script to verify friend recommendation function works without Neo4j warnings.
"""

import os
import sys
import django

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wave_v1.settings")
django.setup()

from socialGraphManagement.recommendations.social.friend import (
    get_friend_recommendations,
)
from authenticationApp.models import CustomUser
import logging

# Setup logging to see any warnings
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_friend_recommendations():
    """Test the friend recommendation function."""
    print("Testing friend recommendations...")

    # Get a test user
    users = CustomUser.objects.filter(is_active=True)[:1]
    if not users:
        print("No active users found for testing")
        return

    test_user = users[0]
    print(f"Testing with user: {test_user.username} (ID: {test_user.user_id})")

    try:
        # Test the function
        recommendations = get_friend_recommendations(str(test_user.user_id), limit=5)
        print(f"Success! Found {len(recommendations)} recommendations:")
        for rec in recommendations:
            print(f"  - User ID: {rec['user_id']}, Score: {rec['score']}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_friend_recommendations()
