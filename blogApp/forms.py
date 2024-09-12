from django import forms
from .models import Blog

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
        
class UpdateBlogTypeForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = [
            "blogType",
        ]


class UpdateBlogTitleForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = [
            "title",
        ]


class UpdateBlogBodyForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = [
            "body",
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
        
class UpdateImageOneForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = [
            "imageOne",
        ]
        
class UpdateImageTwoForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = [
            "imageTwo",
        ]
        
class UpdateImageThreeForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = [
            "imageThree",
        ]
        
class UpdateBlogMoodForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = [
            "mood",
        ]