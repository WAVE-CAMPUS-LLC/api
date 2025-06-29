from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from authenticationApp.models import CustomUser
import random
import string


class Command(BaseCommand):
    help = "Convert existing usernames to new format: prefix#0000"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without actually updating the database",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force update even if username already follows the new format",
        )
        parser.add_argument(
            "--user-id",
            type=str,
            help="Convert specific user by user_id (UUID)",
        )
        parser.add_argument(
            "--email",
            type=str,
            help="Convert specific user by email",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]
        specific_user_id = options["user_id"]
        specific_email = options["email"]

        # Get users to convert
        if specific_user_id:
            try:
                users = CustomUser.objects.filter(user_id=specific_user_id)
            except ValueError:
                raise CommandError(f"Invalid user_id format: {specific_user_id}")
        elif specific_email:
            users = CustomUser.objects.filter(email=specific_email)
        else:
            users = CustomUser.objects.all()

        if not users.exists():
            self.stdout.write(
                self.style.WARNING("No users found matching the criteria.")
            )
            return

        # Filter users that need conversion
        users_to_convert = []
        for user in users:
            # Skip if username already follows new format (contains #) unless force is used
            if "#" in user.username and not force:
                continue
            users_to_convert.append(user)

        if not users_to_convert:
            self.stdout.write(
                self.style.SUCCESS(
                    "All users already have usernames in the new format!"
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(f"Found {len(users_to_convert)} users to convert.")
        )

        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    "DRY RUN MODE - No changes will be made to the database."
                )
            )

        # Convert usernames
        converted_count = 0
        errors = []

        for user in users_to_convert:
            old_username = user.username

            try:
                # Generate new username
                new_username = user.generate_username_from_email()

                if not new_username:
                    errors.append(f"Could not generate username for user {user.email}")
                    continue

                if dry_run:
                    self.stdout.write(
                        f"Would convert: {user.email} | {old_username} -> {new_username}"
                    )
                else:
                    # Update the username
                    with transaction.atomic():
                        user.username = new_username
                        user.save()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Converted: {user.email} | {old_username} -> {new_username}"
                        )
                    )

                converted_count += 1

            except Exception as e:
                error_msg = f"Error converting user {user.email}: {str(e)}"
                errors.append(error_msg)
                self.stdout.write(self.style.ERROR(error_msg))

        # Summary
        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    f"\nDRY RUN COMPLETE: {converted_count} users would be converted."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nCONVERSION COMPLETE: {converted_count} users successfully converted."
                )
            )

        if errors:
            self.stdout.write(self.style.ERROR(f"\n{len(errors)} errors encountered:"))
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))

        # Additional info
        if not dry_run and converted_count > 0:
            self.stdout.write(
                self.style.NOTICE(
                    "\nIMPORTANT: Users may need to be notified of their new usernames!"
                )
            )
