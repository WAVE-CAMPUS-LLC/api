import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings
from adminDashboardApp.models import College
from accountManagementApp.models import UserProfile
from django.core.exceptions import ValidationError


# Create your models here.
class CampusManagerInvite(models.Model):
    college = models.ForeignKey(
        College, on_delete=models.CASCADE, related_name="college_invites"
    )
    email = models.EmailField("Invitee Email")
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    invited_at = models.DateTimeField(default=timezone.now)
    accepted = models.BooleanField(default=False)

    def __str__(self):
        return f"Invite to {self.email} for {self.college.name}"


