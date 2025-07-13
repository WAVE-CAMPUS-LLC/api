from django import forms
from .models import Crew, SurfPost


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


class SurfPostForm(forms.ModelForm):
    class Meta:
        model = SurfPost
        fields = ["content", "event"]

        widgets = {
            "content": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "What's on your mind?",
                    "required": True,
                }
            ),
            "event": forms.Select(
                attrs={
                    "required": True,
                }
            ),
        }

        labels = {
            "event": "Experience",
            "content": "What's on your mind?",
        }
