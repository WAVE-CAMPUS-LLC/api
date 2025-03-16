from django.db import models
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
from django.contrib.auth.models import Group
import uuid
from authenticationApp.models import CustomUser

# Create your models here.
class Blog(models.Model):
    BLOG_TYPE_CHOICES = [("Review", "Review"), ("Anticipation", "Anticipation"), ("Safety", "Safety")]
    MOOD_TYPE_CHOICES = [("Neutral", "Neutral"),("Excited", "Excited"), ("Sad", "Sad"), ("Disappointed", "Disappointed"), ("Satisfactory", "Satisfactory")]
    blogId = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    blogType = models.CharField(
        _("Blog type"), max_length=20, choices=BLOG_TYPE_CHOICES, default=""
    )
    title = models.CharField(max_length=500)
    body = models.TextField(max_length=10000)
    created_at = models.DateTimeField(editable=False, auto_now_add=True)

    imageOne = models.FileField(
        _("First Image"),
        upload_to="blog/images/body/",
        blank=True,
        null=True,
    )

    imageTwo = models.FileField(
        _("Second Image"),
        upload_to="blog/images/body/",
        blank=True,
        null=True,
    )

    imageThree = models.FileField(
        _("Third Image"),
        upload_to="blog/images/body/",
        blank=True,
        null=True,
    )
    
    mood = models.CharField(
        _("How are you feeling?"), max_length=20, choices=MOOD_TYPE_CHOICES, default="Neutral"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blog_created",
    )

    class Meta:
        default_permissions = ()

    def __str__(self):
        return self.title
