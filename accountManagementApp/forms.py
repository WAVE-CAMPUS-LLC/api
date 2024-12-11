from django.utils import timezone
from django import forms
from authenticationApp.models import CustomUser
from .models import UserProfile
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.translation import gettext_lazy as _


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

    birthday = forms.DateField(
        label="When's your birthday?",
        required=True,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        input_formats=["%Y-%m-%d"],
    )

    event_types = forms.MultipleChoiceField(
        choices=EVENT_TYPES_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Select the type of events do you want to see (Maximum 10)",
    )
    
    profile_photo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'custom-file-input'})
    )
    
    

    class Meta:
        model = UserProfile
        fields = [
            "status",
            "gender",
            "profile_photo",
            "college_name",
            "home_state",
            "graduation_year",
            "major",
            "birthday",
            "event_size",
            "event_types",
            "email_communication",
            "text_communication",
        ]

    def clean_graduation_year(self):
        graduation_year = self.cleaned_data["graduation_year"]
        if graduation_year and (
            graduation_year < 1900 or graduation_year > timezone.now().year + 10
        ):
            raise forms.ValidationError("Please enter a valid 4-digit graduation year.")
        return graduation_year


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


# The class `UpdateProfileForm` is a form that allows users to update their profile information, including their status and country.
class UpdateProfileForm(forms.ModelForm):
    status = forms.CharField(required=False, min_length=1)
    country = forms.CharField(required=False)

    class Meta:
        model = UserProfile
        fields = ["status", "country"]
