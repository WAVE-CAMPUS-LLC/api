#!/usr/bin/env python3
"""
Test script for the friend recommendation system.
This script can be run to test the friend recommendation functionality.
"""

import os
import sys
import django

# Add the project root to the Python path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wave_v1.settings")
django.setup()

from socialGraphManagement.recommendations.social.friend import (
    get_friend_recommendations,
    suggest_friends_for_user,
    get_all_users,
    send_friend_recommendation_notification,
)
from authenticationApp.models import CustomUser
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_get_friend_recommendations():
    """Test getting friend recommendations for a user."""
    print("Testing get_friend_recommendations...")

    # Get a test user (first active user)
    users = CustomUser.objects.filter(is_active=True)[:1]
    if not users:
        print("No active users found for testing")
        return

    test_user = users[0]
    print(f"Testing with user: {test_user.username} (ID: {test_user.user_id})")

    try:
        recommendations = get_friend_recommendations(str(test_user.user_id), limit=3)
        print(f"Found {len(recommendations)} recommendations:")
        for rec in recommendations:
            print(f"  - User ID: {rec['user_id']}, Score: {rec['score']}")
    except Exception as e:
        print(f"Error getting recommendations: {e}")


def test_suggest_friends_for_user():
    """Test suggesting friends for a user."""
    print("\nTesting suggest_friends_for_user...")

    # Get a test user
    users = CustomUser.objects.filter(is_active=True)[:1]
    if not users:
        print("No active users found for testing")
        return

    test_user = users[0]
    user_name = test_user.username or str(test_user.user_id)

    try:
        message = suggest_friends_for_user(str(test_user.user_id), user_name)
        print(f"Generated message: {message}")
    except Exception as e:
        print(f"Error suggesting friends: {e}")


def test_get_all_users():
    """Test getting all users."""
    print("\nTesting get_all_users...")

    try:
        users = get_all_users()
        print(f"Found {users.count()} active users")

        # Show first 5 users
        for user in users[:5]:
            print(f"  - {user.username} ({user.user_id})")
    except Exception as e:
        print(f"Error getting users: {e}")


def test_send_notification():
    """Test sending a notification."""
    print("\nTesting send_notification...")

    # Get a test user
    users = CustomUser.objects.filter(is_active=True)[:1]
    if not users:
        print("No active users found for testing")
        return

    test_user = users[0]
    test_message = "This is a test friend recommendation notification!"

    try:
        success = send_friend_recommendation_notification(
            str(test_user.user_id), test_message
        )
        if success:
            print(f"Successfully sent notification to {test_user.username}")
        else:
            print(f"Failed to send notification to {test_user.username}")
    except Exception as e:
        print(f"Error sending notification: {e}")


def main():
    """Run all tests."""
    print("=== Friend Recommendation System Test ===\n")

    test_get_all_users()
    test_get_friend_recommendations()
    test_suggest_friends_for_user()
    test_send_notification()

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    main()
