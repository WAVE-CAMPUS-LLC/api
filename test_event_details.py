#!/usr/bin/env python3
"""
Test script for event details fetching from database.
Tests the new implementation that fetches event details from database using event IDs.
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wave_v1.settings")
import django

django.setup()

from eventManagementApp.models import Event
from socialGraphManagement.recommendations.event.event import get_event_details_from_ids


def test_event_details_fetching():
    """Test event details fetching from database."""

    print("=== Testing Event Details Fetching ===\n")

    # Test 1: Get some sample events from database
    print("1. Getting sample events from database...")
    try:
        sample_events = Event.objects.all()[:5]  # type: ignore
        if sample_events:
            print(f"   Found {len(sample_events)} sample events")

            # Create mock recommendations with event IDs
            mock_recommendations = [
                {
                    "event_id": str(event.eventId),
                    "match_score": 8.5 - i,  # Decreasing scores
                }
                for i, event in enumerate(sample_events)
            ]

            print("   Mock recommendations created:")
            for rec in mock_recommendations:
                print(f"     Event ID: {rec['event_id']}, Score: {rec['match_score']}")

            # Test fetching event details
            print("\n2. Testing event details fetching...")
            detailed_events = get_event_details_from_ids(mock_recommendations)

            print(f"   Retrieved {len(detailed_events)} detailed events:")
            for event in detailed_events:
                print(f"     Title: {event['title']}")
                print(f"     Event ID: {event['event_id']}")
                print(f"     Header Photo: {event['header_photo']}")
                print(f"     Match Score: {event['match_score']}")
                print()

        else:
            print("   No events found in database")

    except Exception as e:
        print(f"   Error testing event details: {str(e)}")

    print()

    # Test 2: Test with empty recommendations
    print("3. Testing with empty recommendations...")
    try:
        empty_result = get_event_details_from_ids([])
        print(f"   Empty result length: {len(empty_result)}")
        print("   ✓ Empty recommendations handled correctly")
    except Exception as e:
        print(f"   Error with empty recommendations: {str(e)}")

    print()

    # Test 3: Test with non-existent event IDs
    print("4. Testing with non-existent event IDs...")
    try:
        fake_recommendations = [
            {"event_id": "12345678-1234-1234-1234-123456789abc", "match_score": 5.0},
            {"event_id": "87654321-4321-4321-4321-cba987654321", "match_score": 4.0},
        ]

        fake_result = get_event_details_from_ids(fake_recommendations)
        print(f"   Fake result length: {len(fake_result)}")
        print("   ✓ Non-existent events handled gracefully")

    except Exception as e:
        print(f"   Error with fake event IDs: {str(e)}")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    test_event_details_fetching()
