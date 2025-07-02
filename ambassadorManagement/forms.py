from django import forms
from .models import AmbassadorApplication, AmbassadorProgramDetails


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


class AmbassadorProgramDetailsForm(forms.ModelForm):
    class Meta:
        model = AmbassadorProgramDetails
        fields = [
            "description",
            "documentation_link",
        ]

        widgets = {
            "description": forms.Textarea(
                attrs={
                    "placeholder": "Enter a detailed description of the ambassador program...",
                    "class": "form-control",
                    "rows": 6,
                }
            ),
            "documentation_link": forms.URLInput(
                attrs={
                    "placeholder": "e.g. https://docs.yoursite.com/ambassador-program",
                    "class": "form-control",
                }
            ),
        }

        labels = {
            "description": "Program Description",
            "documentation_link": "Documentation Link",
        }

        help_texts = {
            "description": "Provide a comprehensive description of the ambassador program, including benefits, requirements, and expectations.",
            "documentation_link": "Link to detailed documentation or guidelines for ambassadors.",
        }
