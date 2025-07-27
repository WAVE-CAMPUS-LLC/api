from django.db import models


# Create your models here.
class AppVersion(models.Model):
    version_id = models.UUIDField(
        primary_key=True,
        help_text="Unique identifier for the app version",
        editable=False,
        unique=True,
        verbose_name="Version ID",
        null=False,
        blank=False,
    )
    platform = models.CharField(
        max_length=50,
        help_text="Platform for the app (e.g., iOS, Android)",
        choices=[("iOS", "iOS"), ("Android", "Android")],
    )
    latest_version = models.CharField(max_length=20, help_text="Latest version number")
    minimum_required_version = models.CharField(
        max_length=20, help_text="Minimum required version number"
    )
    updated_at = models.DateTimeField(auto_now=True, help_text="Last updated timestamp")
