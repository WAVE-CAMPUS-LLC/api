#!/usr/bin/env python3
"""
Test script for personalized event discovery with pagination.
Tests the new event discovery system that prioritizes events based on user preferences.
"""

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
from socialGraphManagement.recommendations.event.event import (
    get_personalized_event_discovery,
    get_event_details_from_ids,
)


def test_event_discovery():
    """Test the personalized event discovery system."""

    print("=== Testing Personalized Event Discovery ===\n")

    # Test 1: User with college
    print("1. Testing user with college...")
    try:
        # Find a user with college
        user_with_college = UserProfile.objects.filter(college__isnull=False).first()  # type: ignore
        if user_with_college and user_with_college.user and user_with_college.college:
            user_id = str(user_with_college.user.user_id)
            college_name = user_with_college.college.name
            print(f"   User ID: {user_id}")
            print(f"   College: {college_name}")

            # Test event discovery
            discovery_results = get_personalized_event_discovery(
                user_id, college_name, 20
            )
            print(f"   Discovery results: {len(discovery_results)} events")

            # Show top 5 events with scores
            for i, event in enumerate(discovery_results[:5]):
                print(
                    f"     {i+1}. Event ID: {event['event_id']}, Score: {event['match_score']}"
                )

            # Test pagination simulation
            print("\n   Testing pagination simulation:")
            page_size = 3
            for page in range(1, 4):
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                page_events = discovery_results[start_idx:end_idx]
                print(f"     Page {page}: {len(page_events)} events")
                for event in page_events:
                    print(
                        f"       - Event ID: {event['event_id']}, Score: {event['match_score']}"
                    )

        else:
            print("   No users with college found")
    except Exception as e:
        print(f"   Error testing user with college: {str(e)}")

    print()

    # Test 2: User without college
    print("2. Testing user without college...")
    try:
        # Find a user without college
        user_without_college = UserProfile.objects.filter(college__isnull=True).first()  # type: ignore
        if user_without_college and user_without_college.user:
            user_id = str(user_without_college.user.user_id)
            print(f"   User ID: {user_id}")
            print(f"   College: None")

            # Test event discovery without college
            discovery_results = get_personalized_event_discovery(user_id, None, 20)
            print(f"   Discovery results: {len(discovery_results)} events")

            # Show top 5 events with scores
            for i, event in enumerate(discovery_results[:5]):
                print(
                    f"     {i+1}. Event ID: {event['event_id']}, Score: {event['match_score']}"
                )

        else:
            print("   No users without college found")
    except Exception as e:
        print(f"   Error testing user without college: {str(e)}")

    print()

    # Test 3: Test event details fetching
    print("3. Testing event details fetching for discovery...")
    try:
        if user_with_college:
            user_id = str(user_with_college.user.user_id)
            college_name = user_with_college.college.name

            # Get discovery results
            discovery_results = get_personalized_event_discovery(
                user_id, college_name, 10
            )

            # Fetch event details
            detailed_events = get_event_details_from_ids(discovery_results)

            print(f"   Retrieved {len(detailed_events)} detailed events:")
            for event in detailed_events[:3]:
                print(f"     Title: {event['title']}")
                print(f"     Event ID: {event['event_id']}")
                print(f"     Header Photo: {event['header_photo']}")
                print(f"     Match Score: {event['match_score']}")
                print()

    except Exception as e:
        print(f"   Error testing event details: {str(e)}")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    test_event_discovery()
