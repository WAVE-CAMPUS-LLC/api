import uuid
from django.db import models
from django.utils.translation import gettext as _
from django.utils import timezone
from django.conf import settings


# Create your models here.
class College(models.Model):
    STATE_CHOICES = [
        ("AL", "Alabama"),
        ("AK", "Alaska"),
        ("AZ", "Arizona"),
        ("AR", "Arkansas"),
        ("CA", "California"),
        ("CO", "Colorado"),
        ("CT", "Connecticut"),
        ("DE", "Delaware"),
        ("FL", "Florida"),
        ("GA", "Georgia"),
        ("HI", "Hawaii"),
        ("ID", "Idaho"),
        ("IL", "Illinois"),
        ("IN", "Indiana"),
        ("IA", "Iowa"),
        ("KS", "Kansas"),
        ("KY", "Kentucky"),
        ("LA", "Louisiana"),
        ("ME", "Maine"),
        ("MD", "Maryland"),
        ("MA", "Massachusetts"),
        ("MI", "Michigan"),
        ("MN", "Minnesota"),
        ("MS", "Mississippi"),
        ("MO", "Missouri"),
        ("MT", "Montana"),
        ("NE", "Nebraska"),
        ("NV", "Nevada"),
        ("NH", "New Hampshire"),
        ("NJ", "New Jersey"),
        ("NM", "New Mexico"),
        ("NY", "New York"),
        ("NC", "North Carolina"),
        ("ND", "North Dakota"),
        ("OH", "Ohio"),
        ("OK", "Oklahoma"),
        ("OR", "Oregon"),
        ("PA", "Pennsylvania"),
        ("RI", "Rhode Island"),
        ("SC", "South Carolina"),
        ("SD", "South Dakota"),
        ("TN", "Tennessee"),
        ("TX", "Texas"),
        ("UT", "Utah"),
        ("VT", "Vermont"),
        ("VA", "Virginia"),
        ("WA", "Washington"),
        ("WV", "West Virginia"),
        ("WI", "Wisconsin"),
        ("WY", "Wyoming"),
    ]

    COUNTRY_CHOICES = [("USA", "United States of America")]

    collegeId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    name = models.CharField(_("College name"), max_length=150)
    address = models.CharField(_("Address"), max_length=500)
    city = models.CharField(_("City"), max_length=20, default="")
    state = models.CharField(
        _("State"), max_length=2, choices=STATE_CHOICES, default=""
    )
    zip_code = models.CharField(_("ZIP Code"), max_length=5)
    country = models.CharField(_("Country"), max_length=5, choices=COUNTRY_CHOICES)

    logo = models.ImageField(
        _("Upload the college logo"), upload_to="college_logos/", blank=True, null=False
    )
    motto = models.CharField(_("What's your college's motto?"), max_length=200)

    contact_website = models.URLField(_("College website"), blank=True, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="college_created",
    )

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

    name = models.CharField(max_length=100)
    description = models.TextField()
    privacy = models.CharField(max_length=30, choices=PRIVACY_CHOICES)

    logo = models.ImageField(upload_to="organization_logos/", blank=True, null=True)

    contact_name = models.CharField(max_length=100)
    contact_email = models.EmailField()
    contact_website = models.URLField(blank=True, null=True)
    contact_phone = models.CharField(max_length=15)

    instagram = models.CharField(max_length=50, blank=True, null=True)
    twitter = models.CharField(max_length=50, blank=True, null=True)
    facebook = models.CharField(max_length=50, blank=True, null=True)
    threads = models.CharField(max_length=50, blank=True, null=True)

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
