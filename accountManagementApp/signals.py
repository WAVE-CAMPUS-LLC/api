from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from accountManagementApp.models import UserProfile
from .utils import generate_profile_picture


@receiver(post_save, sender=UserProfile)
def create_profile_picture(sender, instance, created, **kwargs):
    if created and not instance.profile_photo:
        user = instance.user
        initials = (user.first_name[:1] + user.last_name[:1]).upper()
        profile_photo = generate_profile_picture(initials)
        instance.profile_photo.save(f"{initials}_profile.png", profile_photo, save=True)
