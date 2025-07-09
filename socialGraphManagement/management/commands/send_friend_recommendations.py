from django.core.management.base import BaseCommand
from socialGraphManagement.recommendations.social.friend import (
    send_hourly_friend_recommendations,
)
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send friend recommendations to all active users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run without actually sending notifications",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit the number of users to process (for testing)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]

        self.stdout.write(
            self.style.SUCCESS("Starting friend recommendation process...")
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No notifications will be sent")
            )

        try:
            if dry_run:
                # In dry run mode, just show what would be done
                from socialGraphManagement.recommendations.social.friend import (
                    get_all_users,
                )

                users = get_all_users()
                if limit:
                    users = users[:limit]

                self.stdout.write(
                    f"Would send recommendations to {users.count()} users"
                )
                for user in users[:5]:  # Show first 5 users
                    self.stdout.write(f"  - {user.username} ({user.user_id})")

                if users.count() > 5:
                    self.stdout.write(f"  ... and {users.count() - 5} more users")
            else:
                # Actually run the recommendation system
                result = send_hourly_friend_recommendations()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Friend recommendation process completed successfully!\n"
                        f"  - Successful notifications: {result['successful_notifications']}\n"
                        f"  - Failed notifications: {result['failed_notifications']}\n"
                        f"  - Total users processed: {result['total_users']}"
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error during friend recommendation process: {e}")
            )
            logger.error(f"Error in send_friend_recommendations command: {e}")
            raise
