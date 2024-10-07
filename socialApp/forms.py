from django import forms
from .models import Crew


class createCrewForm(forms.ModelForm):
    class Meta:
        model = Crew
        fields = [
            "name",
            "bio",
        ]

        widgets = {
            "body": forms.Textarea(
                attrs={
                    "class": "",
                    "rows": 5,
                    "cols": 40,
                    "autocomplete": "off",
                    "required": True,
                }
            )
        }
