from django import forms
from .models import AmbassadorApplication


class AmbassadorApplicationForm(forms.ModelForm):
    class Meta:
        model = AmbassadorApplication
        fields = [
            "full_name",
            "college",
            "email",
            "major",
            "instagram_handle",
            "tiktok_handle",
            "graduation_year",
        ]

        widgets = {
            "full_name": forms.TextInput(
                attrs={"placeholder": "e.g. Jane Doe", "class": "form-control"}
            ),
            "college": forms.TextInput(
                attrs={"placeholder": "e.g. Howard University", "class": "form-control"}
            ),
            "email": forms.EmailInput(
                attrs={"placeholder": "e.g. jane@college.edu", "class": "form-control"}
            ),
            "major": forms.TextInput(
                attrs={"placeholder": "e.g. Computer Science", "class": "form-control"}
            ),
            "instagram_handle": forms.TextInput(
                attrs={"placeholder": "e.g. @janedoe", "class": "form-control"}
            ),
            "tiktok_handle": forms.TextInput(
                attrs={"placeholder": "e.g. @janedoe_tiktok", "class": "form-control"}
            ),
            "graduation_year": forms.NumberInput(
                attrs={"placeholder": "e.g. 2026", "class": "form-control"}
            ),
        }

        labels = {
            "full_name": "Full Name",
            "college": "College",
            "email": "Email",
            "major": "Major",
            "instagram_handle": "Instagram Handle",
            "tiktok_handle": "TikTok Handle",
            "graduation_year": "Graduation Year",
        }
