from ast import Pass
from dataclasses import fields
from enum import unique
from pyexpat import model
from django import forms
from authenticationApp.models import CustomUser
from .models import UserProfile
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.translation import gettext_lazy as _


class UserProfileForm(forms.ModelForm):
    """
    The `UserProfileForm` class is a form that allows users to update their profile information, including their status and country.
    """

    class Meta:
        model = UserProfile
        fields = [
            "status",
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


# The class `UpdateProfileForm` is a form that allows users to update their profile information, including their status and country.
class UpdateProfileForm(forms.ModelForm):
    status = forms.CharField(required=False, min_length=1)
    country = forms.CharField(required=False)

    class Meta:
        model = UserProfile
        fields = ["status", "country"]
