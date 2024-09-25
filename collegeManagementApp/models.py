import uuid
from django.db import models
from django.utils.translation import gettext as _
from django.utils import timezone
from django.conf import settings
from urllib.parse import urlparse
from django.core.exceptions import ValidationError
from adminDashboardApp.models import College


# Create your models here.
class CollegeRequest(models.Model):
    name = models.CharField(_("College Name"), max_length=150)
    yourName = models.CharField(_("Your Name"), max_length=100)
    yourEmail = models.EmailField(_("Your Email"), blank=False, null=False)

    def __str__(self):
        return self.name

class Organization(models.Model):
    PRIVACY_CHOICES = [("Private", "Private"), ("Public", "Public")]

    college = models.ForeignKey(
        College, on_delete=models.CASCADE, related_name="organizations"
    )
    orgId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )

    name = models.CharField(_("Organization name"),max_length=100)
    description = models.TextField(_("Describe your org"),)
    privacy = models.CharField(_("Organization privacy?"),max_length=30, choices=PRIVACY_CHOICES)

    logo = models.ImageField(_("Upload an image to represent the org"),upload_to="organization_logos/", blank=True, null=True)

    contact_name = models.CharField(_("Who can we contact? e.g. president, etc"),max_length=100)
    contact_email = models.EmailField(_("What email can we contact?"),)
    contact_website = models.URLField(_("Does the organization have a website?"),blank=True, null=True)

    instagram = models.CharField(_("Connect via Instagram"),max_length=50, blank=True, null=True)

    date_added = models.DateTimeField(auto_now_add=True, editable=False)
    date_modified = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organization_created",
    )

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "college"], name="unique_organization_per_college"
            )
        ]


class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    college = models.ForeignKey(College, on_delete=models.CASCADE)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'college')
        
    def __str__(self):
        return f'{self.user} - {self.college}'
    

class OrganizationMembership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    joined_on = models.DateTimeField(auto_now_add=True)
    
    
    class Meta:
        unique_together = ('user', 'organization')