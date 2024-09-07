from django import forms
from django.contrib.auth.models import Permission, Group
from .models import Blog
from django.utils.translation import gettext_lazy as translate

class createBlogForm(forms.ModelForm):
    
    class Meta:
        model = Blog
        fields = [
            "blogType",
            "title",
            "body",
            "imageOne",
            "imageTwo",
            "imageThree",
            "mood",
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