from dataclasses import fields
from enum import unique
from pyexpat import model
from django import forms
from authenticationApp.models import CustomUser
from .models import UserProfile
from django.utils.translation import gettext_lazy as _


class UpdateUserForm(forms.ModelForm):
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
    email = forms.EmailField(required=False)
    phone_number = forms.CharField(required=False)
    
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        

class UpdateProfileForm(forms.ModelForm):
    status = forms.CharField(required=False,min_length=1)
    country = forms.CharField(required=False)
    
    class Meta:
        model = UserProfile
        fields = ['status', 'country']
    