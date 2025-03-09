import uuid
import re
import qrcode
import requests
import os
import json
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from pathlib import Path
from eventManagementApp.models import Event, SharedEvent
from eventTicketsApp.models import InviteEventOption
from .utils import generate_profile_picture
from django.contrib.auth.models import Group
from collegeManagementApp.models import College
from socialApp.models import CrewMember, CrewRequest, FriendRequest, Crew


# Create your models here.

BASE_DIR = Path(__file__).resolve().parent.parent


class EventTypePreferences(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        default_permissions = ()

    def __str__(self):
        return self.name


def profile_picture_path(instance, filename):
    # Generate a unique path for each profile picture
    ext = filename.split('.')[-1]
    return f'wave/profile-pictures/{instance.user.id}/{uuid.uuid4()}.{ext}'

def get_college_choices():
    """
    Loads a JSON file containing a list of college dictionaries and returns a list of
    tuples in the form (college_name, college_name). This can be used as choices for a model field.
    """
    # Determine the path to the JSON file.
    json_file_path = f'{os.path.join(BASE_DIR, "wave_v1")}/world_universities_and_domains.json'

    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            colleges = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error reading JSON file: {e}")
        # If the file can’t be read or the JSON is invalid, return an empty list.
        return []

    # Create a tuple (value, label) for each college entry.
    college_choices = [
        (college['name'], college['name'])
        for college in colleges
        if college.get('alpha_two_code') == 'US'
    ]
    college_choices.sort(key=lambda choice: choice[0].lower())
    college_choices = college_choices[1:]
    college_choices.append(("Other", "Other"))
    return college_choices


class UserProfile(models.Model):
    COLLEGE_OPTIONS = get_college_choices()
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_profile",
        null=True,
    )
    group = models.ManyToManyField(Group, related_name="user_group")
    college = models.ForeignKey(
        College, null=True, blank=True, on_delete=models.SET_NULL
    )
    friends = models.ManyToManyField("self", symmetrical=True, blank=True)
    is_campus_manager = models.BooleanField(default=False)

    
    profile_photo = models.ImageField(
        upload_to='profile/profile-pictures/',
        null=True,
        blank=True,
        help_text="Profile picture for the user"
    )

    
    was_host = models.BooleanField(default=False)

    # Invited Events
    invited_events = models.ManyToManyField(
        Event, related_name="invited_events", blank=True
    )
    invitations = models.ManyToManyField(
        InviteEventOption, related_name="invitations", blank=True
    )

    profile_qr_code = models.ImageField(
        upload_to="profile/qr_code/", null=True, blank=True
    )
    
    favorite_events = models.ManyToManyField(
        Event, related_name="favorited_by", blank=True, null=True
    )
    
    purchased_events = models.ManyToManyField(
        Event, related_name="purchased_by", blank=True, null=True
    )

    class Meta:
        default_permissions = ()
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return self.user.username

    def generate_qr_code(self):
        part_url = reverse("social:publicProfile", kwargs={"username": self.user.username})
        
        url = f"{settings.SITE_URL}{part_url}"
        qr = qrcode.make(url)

        img_io = BytesIO()
        qr.save(img_io, "PNG")
        img_io.seek(0)

        self.profile_qr_code.save(
            f"{self.user.username}_qr_code.png",
            InMemoryUploadedFile(
                img_io,
                None,
                f"{self.user.username}_qr_code.png",
                "image/png",
                img_io.tell(),
                None,
            ),
            save=False,
        )

    def save(self, *args, event_types=None, **kwargs):
        if not self.profile_qr_code:
            self.generate_qr_code()
        # Now call the parent save method, ensuring to use the correct arguments
        super(UserProfile, self).save(*args, **kwargs)

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

    def is_in_crew(self, crewId):
        receiver = get_object_or_404(CrewMember, user__username=self.user.username)
        if receiver is None:
            return False
        else:
            return Crew.objects.filter(crewId=crewId, members=receiver).exists()

    def has_pending_crew_request(self, other_user):
        return (
            CrewRequest.objects.filter(
                sender=self.user, receiver=other_user, status="pending"
            ).exists()
            or CrewRequest.objects.filter(
                sender=other_user, receiver=self.user, status="pending"
            ).exists()
        )

    def has_declined_crew_request(self, other_user):
        return (
            CrewRequest.objects.filter(
                sender=self.user, receiver=other_user, status="declined"
            ).exists()
            or CrewRequest.objects.filter(
                sender=other_user, receiver=self.user, status="declined"
            ).exists()
        )

    def is_crew_owner(self, crewId):
        crew = get_object_or_404(Crew, crewId=crewId)
        return crew.created_by == self.user

    def get_all_crews(self):
        return [member.crew for member in CrewMember.objects.filter(user=self.user).select_related('crew')]

    def get_shared_events(self):
        return SharedEvent.objects.filter(receiver=self.user)
