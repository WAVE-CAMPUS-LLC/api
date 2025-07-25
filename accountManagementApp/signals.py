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
        if not user or not user.first_name or not user.last_name:
            return  # Skip profile picture generation if user info is incomplete
        
        try:
            profile_photo = generate_profile_picture(user.first_name, user.last_name)
            initials = (user.first_name[:1] + user.last_name[:1]).upper()
            instance.profile_photo.save(f"{initials}_profile.png", profile_photo, save=True)
        except Exception as e:
            print(f"Error generating profile picture for {user.username if user else 'unknown'}: {e}")


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
