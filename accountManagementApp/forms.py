from django.utils import timezone
from django import forms
from authenticationApp.models import CustomUser
from .models import UserProfile, EventTypePreferences
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.translation import gettext_lazy as _


from .models import EventTypePreferences




class UpdateProfilePhotoForm(forms.ModelForm):
    """
    The `UpdateProfilePhotoForm` class is a form that allows users to update their profile photo.
    """

    profile_photo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={"class": "custom-file-input"}),
        label="Profile picture",
    )

    class Meta:
        model = UserProfile
        fields = ["profile_photo"]

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

