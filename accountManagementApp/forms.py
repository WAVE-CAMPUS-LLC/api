from django.utils import timezone
from django import forms
from authenticationApp.models import CustomUser
from .models import UserProfile, EventTypePreferences
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.translation import gettext_lazy as _


from .models import EventTypePreferences


class UserProfileForm(forms.ModelForm):
    """
    The `UserProfileForm` class is a form that allows users to update their profile information, including their status and country.
    """

    EVENT_TYPES_CHOICES = [
        ("Homecoming", "Homecoming"),
        ("Concert", "Concert"),
        ("Greek", "Greek"),
        ("Party", "Party"),
        ("Career Fair", "Career Fair"),
        ("Networking Event", "Networking Event"),
        ("Fundraiser", "Fundraiser"),
        ("Game Night", "Game Night"),
        ("Open Mic Night", "Open Mic Night"),
        ("Sports Tournament", "Sports Tournament"),
        ("Basketball Game", "Basketball Game"),
        ("Football Game", "Football Game"),
        ("Tailgate", "Tailgate"),
        ("Picnic", "Picnic"),
        ("Cookout", "Cookout"),
        ("Alumni Meetup", "Alumni Meetup"),
        ("Workshop", "Workshop"),
        ("Music Festival", "Music Festival"),
        ("Comedy Show", "Comedy Show"),
        ("Dance Party", "Dance Party"),
        ("Talent Show", "Talent Show"),
        ("Movie Night", "Movie Night"),
        ("Karaoke Night", "Karaoke Night"),
        ("Scavenger Hunt", "Scavenger Hunt"),
        ("Hackathon", "Hackathon"),
        ("Volunteer Event", "Volunteer Event"),
        ("Fashion Show", "Fashion Show"),
        ("Dance Competition", "Dance Competition"),
        ("Job Fair", "Job Fair"),
    ]

    event_types = forms.MultipleChoiceField(
        choices=EVENT_TYPES_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Select the type of events do you want to see (Maximum 10)",
    )

    profile_photo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={"class": "custom-file-input"}),
        label="Profile picture",
    )

    class Meta:
        model = UserProfile
        fields = [
            "status",
            "gender",
            "profile_photo",
            "college_name",
            "instagram",
            "tiktok",
            "home_state",
            "graduation_year",
            "major",
            "event_types",
        ]

    def clean_event_types(self):
        event_types = self.cleaned_data.get("event_types")
        if len(event_types) > 10:
            raise forms.ValidationError("You can select a maximum of 10 event types.")

        # Convert the event type names to EventTypePreferences model instances
        event_type_instances = []
        for event_type_name in event_types:
            # Fetch or create the EventTypePreferences instance
            event_type_instance, created = EventTypePreferences.objects.get_or_create(
                name=event_type_name
            )
            event_type_instances.append(event_type_instance)

        return event_type_instances


class EditUserProfileForm(forms.ModelForm):
    """
    The `EditUserProfileForm` class is a form that allows users to update their profile information, including their status and country.
    """

    EVENT_TYPES_CHOICES = [
        ("Homecoming", "Homecoming"),
        ("Concert", "Concert"),
        ("Greek", "Greek"),
        ("Party", "Party"),
        ("Career Fair", "Career Fair"),
        ("Networking Event", "Networking Event"),
        ("Fundraiser", "Fundraiser"),
        ("Game Night", "Game Night"),
        ("Open Mic Night", "Open Mic Night"),
        ("Sports Tournament", "Sports Tournament"),
        ("Basketball Game", "Basketball Game"),
        ("Football Game", "Football Game"),
        ("Tailgate", "Tailgate"),
        ("Picnic", "Picnic"),
        ("Cookout", "Cookout"),
        ("Alumni Meetup", "Alumni Meetup"),
        ("Workshop", "Workshop"),
        ("Music Festival", "Music Festival"),
        ("Comedy Show", "Comedy Show"),
        ("Dance Party", "Dance Party"),
        ("Talent Show", "Talent Show"),
        ("Movie Night", "Movie Night"),
        ("Karaoke Night", "Karaoke Night"),
        ("Scavenger Hunt", "Scavenger Hunt"),
        ("Hackathon", "Hackathon"),
        ("Volunteer Event", "Volunteer Event"),
        ("Fashion Show", "Fashion Show"),
        ("Dance Competition", "Dance Competition"),
        ("Job Fair", "Job Fair"),
    ]

    status = forms.ChoiceField(
        choices=UserProfile.USER_STATUS_OPTION,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )


    class Meta:
        model = UserProfile
        fields = [
            "status",
            "college_name",
            "instagram",
            "tiktok",
            "home_state",
            "graduation_year",
            "major",
        ]


# The class UpdateContactInfo is a form that allows users to update their email and phone number information. Used in the accountManagementApp/views.py
class UpdateContactInfo(forms.ModelForm):

    email = forms.EmailField(required=False)
    phone_number = forms.CharField(required=False)

    class Meta:
        model = CustomUser
        fields = ["email", "phone_number"]


# The class `UpdatePersonalInfo` is a form that allows users to update their first name and last name. Used in the accountManagementApp/views.py
class UpdatePersonalInfo(forms.ModelForm):
    first_name = forms.CharField(
        required=False,
        max_length=50,
        help_text=(_("First Name")),
    )
    last_name = forms.CharField(
        required=False,
        max_length=50,
        help_text=(_("Last Name")),
    )

    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name"]

