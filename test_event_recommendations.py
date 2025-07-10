#!/usr/bin/env python3
"""
Test script for event recommendation system with college auto-detection.
Tests both users with college and users without college.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wave_v1.settings")
import django

django.setup()

from authenticationApp.models import CustomUser
from accountManagementApp.models import UserProfile
from collegeManagementApp.models import College
from socialGraphManagement.recommendations.event.event import (
    get_event_recommendations_for_user,
)


def test_event_recommendations():
    """Test event recommendations for different user types."""

    print("=== Testing Event Recommendation System ===\n")

    # Test 1: User with college
    print("1. Testing user with college...")
    try:
        # Find a user with college
        user_with_college = UserProfile.objects.filter(college__isnull=False).first()
        if user_with_college:
            user_id = str(user_with_college.user.user_id)
            college_name = user_with_college.college.name
            print(f"   User ID: {user_id}")
            print(f"   College: {college_name}")

            # Test with explicit college name
            recommendations = get_event_recommendations_for_user(
                user_id, college_name, 5
            )
            print(f"   Recommendations with college: {len(recommendations)}")

            # Test with None college (should auto-detect)
            recommendations_none = get_event_recommendations_for_user(user_id, None, 5)
            print(f"   Recommendations with None college: {len(recommendations_none)}")

        else:
            print("   No users with college found")
    except Exception as e:
        print(f"   Error testing user with college: {str(e)}")

    print()

    # Test 2: User without college
    print("2. Testing user without college...")
    try:
        # Find a user without college
        user_without_college = UserProfile.objects.filter(college__isnull=True).first()
        if user_without_college:
            user_id = str(user_without_college.user.user_id)
            print(f"   User ID: {user_id}")
            print(f"   College: None")

            # Test with None college
            recommendations = get_event_recommendations_for_user(user_id, None, 5)
            print(f"   Recommendations without college: {len(recommendations)}")

            # Test with explicit None
            recommendations_explicit = get_event_recommendations_for_user(
                user_id, None, 5
            )
            print(
                f"   Recommendations with explicit None: {len(recommendations_explicit)}"
            )

        else:
            print("   No users without college found")
    except Exception as e:
        print(f"   Error testing user without college: {str(e)}")

    print()

    # Test 3: Edge cases
    print("3. Testing edge cases...")
    try:
        # Test with non-existent user
        recommendations = get_event_recommendations_for_user(
            "non-existent-user", "Test College", 5
        )
        print(f"   Non-existent user recommendations: {len(recommendations)}")

        # Test with empty string college
        if user_with_college:
            user_id = str(user_with_college.user.user_id)
            recommendations = get_event_recommendations_for_user(user_id, "", 5)
            print(f"   Empty string college recommendations: {len(recommendations)}")

    except Exception as e:
        print(f"   Error testing edge cases: {str(e)}")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    test_event_recommendations()
