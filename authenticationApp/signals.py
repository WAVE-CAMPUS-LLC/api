from django.db.models.signals import post_migrate
from django.dispatch import receiver
import os


@receiver(post_migrate)
def auto_convert_usernames(sender, **kwargs):
    """
    Automatically convert usernames after migrations if enabled
    Set environment variable AUTO_CONVERT_USERNAMES=true to enable
    """
    # Only run for authenticationApp migrations
    if sender.name != "authenticationApp":
        return

    # Check if auto-conversion is enabled via environment variable
    if not os.getenv("AUTO_CONVERT_USERNAMES", "").lower() == "true":
        return

    from .models import CustomUser

    # Get users that need conversion
    users_to_convert = CustomUser.objects.exclude(username__contains="#")

    if not users_to_convert.exists():
        print("✅ All usernames already in new format!")
        return

    print(f"🔄 Auto-converting {users_to_convert.count()} usernames...")

    converted_count = 0
    for user in users_to_convert:
        try:
            old_username = user.username
            new_username = user.generate_username_from_email()

            if new_username:
                user.username = new_username
                user.save()
                print(f"✅ {user.email}: {old_username} -> {new_username}")
                converted_count += 1

        except Exception as e:
            print(f"❌ Error converting {user.email}: {str(e)}")

    print(f"🎉 Auto-converted {converted_count} usernames!")
