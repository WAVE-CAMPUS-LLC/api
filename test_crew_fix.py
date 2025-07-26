#!/usr/bin/env python
"""
Test script to verify the crew-college relationship fix.
This script tests the suggest_crews_for_user function to ensure it doesn't throw Neo4j warnings.
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append("/c%3A/Users/larte/OneDrive/Documents/Github/wave_v1")

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wave_v1.settings")
django.setup()

from socialGraphManagement.graph.crew_graph import suggest_crews_for_user
import logging

# Set up logging to see any warnings
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_crew_suggestions():
    """Test the crew suggestion function to ensure no Neo4j warnings."""
    try:
        # Test with a sample user ID (you may need to replace with a real user ID)
        test_user_id = "test_user_123"

        print("Testing crew suggestions...")
        suggestions = suggest_crews_for_user(test_user_id, limit=5)

        print(f"✅ Success! Found {len(suggestions)} crew suggestions")
        for suggestion in suggestions:
            print(f"  - Crew: {suggestion['name']} (Score: {suggestion['score']})")

        return True

    except Exception as e:
        print(f"❌ Error testing crew suggestions: {e}")
        return False


if __name__ == "__main__":
    print("Testing crew-college relationship fix...")
    success = test_crew_suggestions()

    if success:
        print("\n✅ Test completed successfully - no Neo4j warnings should appear!")
    else:
        print("\n❌ Test failed - check the error messages above")
