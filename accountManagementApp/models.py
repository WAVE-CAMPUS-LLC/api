from django.db import models
from django.utils.translation import gettext_lazy as translate
from django.conf import settings
from django.contrib.auth.models import Group
from collegeManagementApp.models import College
from socialApp.models import FriendRequest


# Create your models here.


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_profile"
    )
    status = models.TextField(blank=True)
    country = models.CharField(max_length=100, blank=True)
    group = models.ManyToManyField(Group, related_name="user_group")
    college = models.ForeignKey(
        College, null=True, blank=True, on_delete=models.SET_NULL
    )
    friends = models.ManyToManyField(
        "self", symmetrical=True, blank=True, related_name="related_friends"
    )
    
    is_campus_manager = models.BooleanField(default=False)

    class Meta:
        default_permissions = ()
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def is_friends_with(self, other_user):
        return self.friends.filter(
            user=other_user
        ).exists() and not self.has_pending_request(other_user)  

    def has_pending_request(self, other_user):
        return (
            FriendRequest.objects.filter(
                sender=self.user, receiver=other_user, status="pending"
            ).exists()
            or FriendRequest.objects.filter(
                sender=other_user, receiver=self.user, status="pending"
            ).exists()
        )

    def has_declined_request(self, other_user):
        return (
            FriendRequest.objects.filter(
                sender=self.user, receiver=other_user, status="declined"
            ).exists()
            or FriendRequest.objects.filter(
                sender=other_user, receiver=self.user, status="declined"
            ).exists()
        )
