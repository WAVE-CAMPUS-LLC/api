#!/usr/bin/env python3
"""
Test script to verify the async database calls work correctly.
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wave_v1.settings")
import django

django.setup()

import asyncio
from channels.db import database_sync_to_async
from socialGraphManagement.recommendations.event.event import get_event_details_from_ids


async def test_async_database_calls():
    """Test that the database calls work in async context."""

    print("=== Testing Async Database Calls ===\n")

    try:
        # Get some sample events
        from eventManagementApp.models import Event

        @database_sync_to_async
        def get_sample_events():
            return list(Event.objects.all()[:3])  # type: ignore

        sample_events = await get_sample_events()

        if sample_events:
            # Create mock recommendations
            mock_recommendations = [
                {"event_id": str(event.eventId), "match_score": 8.5 - i}
                for i, event in enumerate(sample_events)
            ]

            print(f"Testing with {len(mock_recommendations)} mock recommendations...")

            # Test the async version
            detailed_events = await database_sync_to_async(get_event_details_from_ids)(
                mock_recommendations
            )

            print(f"✓ Successfully retrieved {len(detailed_events)} detailed events")
            for event in detailed_events:
                print(f"  - {event['title']} (ID: {event['event_id']})")

        else:
            print("No events found in database")

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_async_database_calls())
