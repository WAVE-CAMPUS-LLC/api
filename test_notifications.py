#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wave_v1.settings")
django.setup()

from authenticationApp.models import CustomUser
from django.utils import timezone
from accountManagementApp.models import MoodEntry
import asyncio
from apiManager.notifications.notification import send_notification


def test_notifications():
    print("Testing notification system...")

    try:
        # Get all users
        users = CustomUser.objects.all()
        print(f"Found {users.count()} users")

        if users.count() == 0:
            print("No users found in database")
            return

        for user in users:
            print(f"\nChecking user: {user.username} (ID: {user.user_id})")

            # Check if user has filled mood today
            try:
                has_filled_today = user.mood_entries.filter(date=timezone.now().date()).exists()  # type: ignore
                print(f"  Has filled mood today: {has_filled_today}")

                if not has_filled_today:
                    print(f"  Sending notification to {user.username}")

                    message = "Tell us how you're feeling! Let's see what the move is!"
                    title = "What's the move today?!"
                    navigate_to = "mood_entry"
                    params = {"date": timezone.now().date().isoformat()}

                    try:
                        # Send notification
                        result = asyncio.run(
                            send_notification(
                                user.user_id,
                                message,
                                title=title,
                                navigate_to=navigate_to,
                                params=params,
                            )
                        )
                        if result:
                            print(
                                f"  ✅ Notification sent successfully to {user.username}"
                            )
                        else:
                            print(
                                f"  ❌ Failed to send notification to {user.username}"
                            )
                    except Exception as e:
                        print(
                            f"  ❌ Error sending notification to {user.username}: {str(e)}"
                        )
                else:
                    print(f"  Skipping {user.username} - already filled mood today")

            except Exception as e:
                print(f"  ❌ Error checking mood entries for {user.username}: {str(e)}")

    except Exception as e:
        print(f"Error in test: {str(e)}")


if __name__ == "__main__":
    test_notifications()
