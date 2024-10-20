from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils.timezone import now
from .models import UserActivity, GlobalUserStats

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    UserActivity.objects.create(user=user, action='login', timestamp=now())

    global_stats, created = GlobalUserStats.objects.get_or_create(id=1)
    global_stats.total_logins += 1
    global_stats.save()

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    UserActivity.objects.create(user=user, action='logout', timestamp=now())

    global_stats, created = GlobalUserStats.objects.get_or_create(id=1)
    global_stats.total_logouts += 1
    global_stats.save()
