from django.db.models.signals import post_save, post_migrate
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from accountManagementApp.models import UserProfile, UserPreferences
from .utils import generate_profile_picture


@receiver(post_save, sender=UserProfile)
def create_profile_picture(sender, instance, created, **kwargs):
    if created and not instance.profile_photo:
        user = instance.user
        # Safely handle missing user information
        if not user:
            return  # Skip profile picture generation if user is missing

        try:
            # Handle the case where first_name and last_name are the same (generated username)
            first_name = user.first_name
            last_name = user.last_name

            # If both names are the same (likely a generated username), extract meaningful initials
            if first_name and last_name and first_name == last_name:
                # Extract the part before the # symbol if it exists
                name_parts = first_name.split("#")[0]
                if len(name_parts) >= 2:
                    # Use first two characters of the username part
                    initials = name_parts[:2].upper()
                else:
                    # Fallback to first character
                    initials = name_parts[:1].upper() if name_parts else "U"
            else:
                # Normal case: use first letter of first and last name
                initials = ""
                if first_name and len(first_name) > 0:
                    initials += first_name[0].upper()
                if last_name and len(last_name) > 0:
                    initials += last_name[0].upper()

                if not initials:
                    initials = "U"  # Default for users with no name info

            profile_photo = generate_profile_picture(first_name, last_name)

            if profile_photo:
                # Convert PIL Image to Django-compatible file
                from io import BytesIO
                from django.core.files.base import ContentFile

                # Save PIL image to BytesIO
                img_io = BytesIO()
                profile_photo.save(img_io, format="PNG")
                img_io.seek(0)

                # Create ContentFile for Django
                content_file = ContentFile(img_io.getvalue())

                # Save to the model field
                instance.profile_photo.save(
                    f"{initials}_profile.png", content_file, save=True
                )
                print(f"Generated profile picture for user: {user.username}")
            else:
                print(f"Failed to generate profile picture for user: {user.username}")

        except Exception as e:
            print(
                f"Error generating profile picture for {user.username if user else 'unknown'}: {e}"
            )


@receiver(post_save, sender=UserProfile)
def create_user_preferences(sender, instance, created, **kwargs):
    if created:
        try:
            UserPreferences.objects.create(
                user=instance.user, profile=instance, college=instance.college
            )
        except Exception as e:
            print(f"Error creating user preferences: {e}")


@receiver(post_migrate)
def create_missing_user_preferences(sender, **kwargs):
    """
    Create user preferences for existing users who don't have them.
    This runs after migrations are complete, ensuring tables exist.
    """
    # Only run for our app to avoid running multiple times
    if sender.name != "accountManagementApp":
        return

    try:
        User = get_user_model()
        created_count = 0

        # Get all users with profiles
        profiles = UserProfile.objects.select_related("user").all()

        for profile in profiles:
            user = profile.user
            if user:  # Safety check
                try:
                    # Check if user preferences already exist
                    existing_prefs = UserPreferences.objects.filter(user=user).first()
                    if not existing_prefs:
                        UserPreferences.objects.create(
                            user=user, profile=profile, college=profile.college
                        )
                        created_count += 1
                        print(f"✅ Created user preferences for {user.email}")
                except Exception as e:
                    print(
                        f"❌ Error creating preferences for {user.email if user else 'unknown'}: {e}"
                    )

        if created_count > 0:
            print(f"🎉 Successfully created {created_count} user preferences")
        else:
            print("✨ All users already have preferences")

    except Exception as e:
        print(f"⚠️ Error in create_missing_user_preferences: {e}")
