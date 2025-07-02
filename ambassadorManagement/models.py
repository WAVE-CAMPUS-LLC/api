from django.db import models
from django.utils.translation import gettext_lazy as _
import datetime
from datetime import timedelta, date
from django.contrib.postgres.indexes import GinIndex, OpClass
import uuid
from authenticationApp.models import CustomUser


# Create your models here.
class AmbassadorProgramDetails(models.Model):
    description = models.TextField(verbose_name="Description")
    documentation_link = models.URLField(verbose_name="Documentation link")


class AmbassadorProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    referral_code = models.CharField(max_length=7, unique=True)
    joined_date = models.DateTimeField(auto_now_add=True)


class AmbassadorApplication(models.Model):
    app_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    full_name = models.CharField(
        max_length=100, verbose_name="Full Name", null=False, blank=False
    )
    college = models.CharField(
        max_length=100, verbose_name="College", null=False, blank=False
    )
    email = models.EmailField(
        _("Email"), unique=True, blank=False, null=False, help_text=(_("Email"))
    )
    instagram_handle = models.CharField(
        max_length=100, verbose_name="Instagram Handle", null=False, blank=False
    )
    major = models.CharField(
        max_length=100, verbose_name="Major", null=False, blank=False
    )
    tiktok_handle = models.CharField(
        max_length=100, verbose_name="TikTok Handle", null=False, blank=False
    )
    graduation_year = models.PositiveBigIntegerField(blank=False, null=False)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
        ],
        default="pending",
    )
    application_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} – {self.college}"
