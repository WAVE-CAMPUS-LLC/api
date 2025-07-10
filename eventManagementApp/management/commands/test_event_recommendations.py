from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from authenticationApp.models import CustomUser
from accountManagementApp.models import UserProfile
from collegeManagementApp.models import College
from socialGraphManagement.recommendations.event.event import (
    get_event_recommendations_for_user,
)
import json

User = get_user_model()


class Command(BaseCommand):
    help = "Test event recommendation system with college auto-detection"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            type=str,
            help="Specific user ID to test",
        )
        parser.add_argument(
            "--college-name",
            type=str,
            help="Specific college name to test",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
            help="Number of recommendations to fetch",
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("=== Testing Event Recommendation System ===\n")
        )

        user_id = options.get("user_id")
        college_name = options.get("college_name")
        limit = options.get("limit")

        if user_id:
            # Test specific user
            self.test_specific_user(user_id, college_name, limit)
        else:
            # Test different user types
            self.test_all_user_types(limit)

    def test_specific_user(self, user_id, college_name, limit):
        """Test event recommendations for a specific user."""
        self.stdout.write(f"Testing user ID: {user_id}")

        try:
            # Test with provided college name
            if college_name:
                recommendations = get_event_recommendations_for_user(
                    user_id, college_name, limit
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Recommendations with college '{college_name}': {len(recommendations)}"
                    )
                )
                for i, rec in enumerate(recommendations[:3], 1):
                    self.stdout.write(
                        f"  {i}. {rec['title']} (Score: {rec['match_score']})"
                    )

            # Test with None college (auto-detection)
            recommendations_none = get_event_recommendations_for_user(
                user_id, None, limit
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Recommendations with auto-detection: {len(recommendations_none)}"
                )
            )
            for i, rec in enumerate(recommendations_none[:3], 1):
                self.stdout.write(
                    f"  {i}. {rec['title']} (Score: {rec['match_score']})"
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error testing user {user_id}: {str(e)}")
            )

    def test_all_user_types(self, limit):
        """Test event recommendations for different user types."""

        # Test 1: User with college
        self.stdout.write("1. Testing user with college...")
        try:
            user_with_college = UserProfile.objects.filter(
                college__isnull=False
            ).first()
            if user_with_college:
                user_id = str(user_with_college.user.user_id)
                college_name = user_with_college.college.name
                self.stdout.write(f"   User ID: {user_id}")
                self.stdout.write(f"   College: {college_name}")

                # Test with explicit college name
                recommendations = get_event_recommendations_for_user(
                    user_id, college_name, limit
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"   Recommendations with college: {len(recommendations)}"
                    )
                )

                # Test with None college (should auto-detect)
                recommendations_none = get_event_recommendations_for_user(
                    user_id, None, limit
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"   Recommendations with None college: {len(recommendations_none)}"
                    )
                )

            else:
                self.stdout.write("   No users with college found")
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"   Error testing user with college: {str(e)}")
            )

        self.stdout.write("")

        # Test 2: User without college
        self.stdout.write("2. Testing user without college...")
        try:
            user_without_college = UserProfile.objects.filter(
                college__isnull=True
            ).first()
            if user_without_college:
                user_id = str(user_without_college.user.user_id)
                self.stdout.write(f"   User ID: {user_id}")
                self.stdout.write(f"   College: None")

                # Test with None college
                recommendations = get_event_recommendations_for_user(
                    user_id, None, limit
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"   Recommendations without college: {len(recommendations)}"
                    )
                )

                # Test with explicit None
                recommendations_explicit = get_event_recommendations_for_user(
                    user_id, None, limit
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"   Recommendations with explicit None: {len(recommendations_explicit)}"
                    )
                )

            else:
                self.stdout.write("   No users without college found")
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"   Error testing user without college: {str(e)}")
            )

        self.stdout.write("")

        # Test 3: Edge cases
        self.stdout.write("3. Testing edge cases...")
        try:
            # Test with non-existent user
            recommendations = get_event_recommendations_for_user(
                "non-existent-user", "Test College", limit
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"   Non-existent user recommendations: {len(recommendations)}"
                )
            )

            # Test with empty string college
            if user_with_college:
                user_id = str(user_with_college.user.user_id)
                recommendations = get_event_recommendations_for_user(user_id, "", limit)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"   Empty string college recommendations: {len(recommendations)}"
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"   Error testing edge cases: {str(e)}")
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== Test Complete ==="))
