import uuid
from django.db import models
from django.utils.translation import gettext as _
from django.utils import timezone
from django.conf import settings
from urllib.parse import urlparse
from django.core.exceptions import ValidationError
from adminDashboardApp.models import College


# Create your models here.
from django.db import models

class CollegeRequest(models.Model):
    requestId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    name = models.CharField(_("College Name"), max_length=150)
    yourName = models.CharField(_("Your Name"), max_length=100)
    yourEmail = models.EmailField(_("Your Email"), blank=False, null=False)

    def __str__(self):
        return self.name
    
    class Meta:
        default_permissions = ()


class Organization(models.Model):
    PRIVACY_CHOICES = [
        ("Private", "Private"),
        ("Public", "Public"),
    ]
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Accepted", "Accepted"),
        ("Denied", "Denied"),
    ]

    college = models.ForeignKey(
        College, on_delete=models.CASCADE, related_name="organizations"
    )
    orgId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )

    name = models.CharField(_("Organization name"), max_length=100)
    description = models.TextField(
        _("Describe your org"),
    )
    privacy = models.CharField(
        _("Organization privacy?"), max_length=30, choices=PRIVACY_CHOICES
    )
    status = models.CharField(
        _("Approval Status"), max_length=10, choices=STATUS_CHOICES, default="Pending"
    )
    logo = models.FileField(
        _("Upload an image to represent the org"),
        upload_to="organization_logos/",
        blank=True,
        null=True,
    )

    contact_name = models.CharField(
        _("Who can we contact? e.g. president, etc"), max_length=100
    )
    contact_email = models.EmailField(
        _("What email can we contact?"),
    )
    contact_website = models.URLField(
        _("Does the organization have a website?"), blank=True, null=True
    )

    instagram = models.CharField(
        _("Connect via Instagram"), max_length=50, blank=True, null=True
    )

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
        
        default_permissions = ()


class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    college = models.ForeignKey(College, on_delete=models.CASCADE)
    date_joined = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "college")
        default_permissions = ()

    def __str__(self):
        return f"{self.user} - {self.college}"


class OrganizationMembership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="org_memberships")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    joined_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "organization")
        default_permissions = ()


Event = "eventManagementApp.Event"
class CollegeEventLink(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name="college_events")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="linked_colleges")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        default_permissions = ()
        unique_together = ("college", "event")
        
    def __str__(self):
        return f'{self.college.name} - {self.event.title}'