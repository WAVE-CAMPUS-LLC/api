from django import forms
from .models import College, Organization


class CollegeForm(forms.ModelForm):
    class Meta:
        model = College
        fields = [
            "name",
            "address",
            "city",
            "state",
            "zip_code",
            "country",
            "logo",
            "motto",
            "contact_website",
        ]

        widgets = {"state": forms.Select(), "country": forms.Select()}


class JoinCollegeForm(forms.Form):
    email = forms.EmailField(
        label="College Email",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your college email",
                "required": "required",
            }
        ),
    )


class VerifyCollegeJoinForm(forms.Form):
    code = forms.CharField(
        label="Code",
        max_length=6,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter the verification code",
                "required": "required",
            }
        ),
    )
