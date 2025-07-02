from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AmbassadorProfile
from authenticationApp.models import CustomUser
from ambassadorManagement.utils import generate_referral_code


@receiver(post_save, sender=CustomUser)
def create_ambassador_profile(sender, instance, created, **kwargs):
    if instance.is_tide_ambassador:
        profile, created = AmbassadorProfile.objects.get_or_create(user=instance)

        if not profile.referral_code:
            referral_code = generate_referral_code()
            while AmbassadorProfile.objects.filter(
                referral_code=referral_code
            ).exists():
                referral_code = generate_referral_code()

            profile.referral_code = referral_code
            profile.save()

    else:
        AmbassadorProfile.objects.filter(user=instance).delete()
