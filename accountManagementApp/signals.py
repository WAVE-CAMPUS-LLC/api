from django.db.models.signals import post_save
from django.dispatch import receiver
from accountManagementApp.models import UserProfile
from .utils import generate_profile_picture




@receiver(post_save, sender=UserProfile)
def create_profile_picture(sender, instance, created, **kwargs):
    if created and not instance.profile_photo:
        initials = (instance.first_name[:1] + instance.last_name[:1]).upper()
        profile_photo = generate_profile_picture(initials)
        instance.profile_photo.save(f"{initials}_profile.png", generate_profile_picture())