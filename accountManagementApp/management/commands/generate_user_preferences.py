from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accountManagementApp.models import UserProfile, UserPreferences


User = get_user_model()


class Command(BaseCommand):
    help = "Generate user preferences for all users"

    def handle(self, *args, **options):
        users = User.objects.all()
        created = 0
        skipped = 0

        for user in users:
            try:
                profile = user.user_profile

            except UserProfile.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"User {user.email} has no profile")
                )
                skipped += 1
                continue

            if hasattr(user, "user_preferences"):
                self.stdout.write(
                    self.style.SUCCESS(f"User {user.email} already has preferences")
                )
                skipped += 1
                continue

            UserPreferences.objects.create(
                user=user,
                profile=profile,
                college=profile.college,
            )

            created += 1
            self.stdout.write(
                self.style.SUCCESS(f"Generated user preferences for {user.email}")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Generated {created} user preferences, skipped {skipped} users"
            )
        )
