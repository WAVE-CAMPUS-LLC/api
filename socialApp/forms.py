from django import forms
from .models import Crew, SurfPost, FixedMessage


class createCrewForm(forms.ModelForm):
    class Meta:
        model = Crew
        fields = [
            "name",
            "bio",
            "crew_image",
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
            ),
            "crew_image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control-file",
                    "accept": "image/*",
                }
            ),
        }


class EditCrewImageForm(forms.Form):
    crew_image = forms.ImageField(
        required=True,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control-file",
                "accept": "image/*",
            }
        ),
        help_text="Upload a new crew image",
    )


class EditCrewNameForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter crew name",
                "maxlength": "100",
                "required": True,
                "autocomplete": "off",
            }
        ),
        help_text="Enter the new crew name (max 100 characters)",
    )

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if name:
            name = name.strip()
            if not name:
                raise forms.ValidationError("Crew name cannot be empty")
            self.cleaned_data["name"] = name
        return name


class EditCrewBioForm(forms.Form):
    bio = forms.CharField(
        max_length=500,
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 5,
                "cols": 40,
                "placeholder": "Enter crew bio",
                "maxlength": "500",
                "required": True,
                "autocomplete": "off",
            }
        ),
        help_text="Enter the new crew bio (max 500 characters)",
    )

    def clean_bio(self):
        bio = self.cleaned_data.get("bio")
        if bio:
            bio = bio.strip()
            if not bio:
                raise forms.ValidationError("Crew bio cannot be empty")
            self.cleaned_data["bio"] = bio
        return bio


class SurfPostForm(forms.ModelForm):
    class Meta:
        model = SurfPost
        fields = ["event", "content"]

        widgets = {
            "event": forms.Select(
                attrs={
                    "required": True,
                }
            ),
            "content": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "What's on your mind?",
                    "required": True,
                }
            ),
        }

        labels = {
            "event": "Experience",
            "content": "How you feelin'?",
        }


class FixedMessageForm(forms.ModelForm):
    class Meta:
        model = FixedMessage
        fields = ["text"]

        widgets = {
            "text": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter fixed message text",
                    "maxlength": "255",
                    "required": True,
                    "autocomplete": "off",
                }
            )
        }

        labels = {
            "text": "Message Text",
        }

        help_texts = {
            "text": "Enter the text for the fixed message (max 255 characters)",
        }

    def clean_text(self):
        """
        Custom validation for the text field
        """
        text = self.cleaned_data.get("text")
        if text:
            # Strip whitespace
            text = text.strip()

            # Check if text is not empty after stripping
            if not text:
                raise forms.ValidationError("Message text cannot be empty")

            # Check if message with same text already exists
            if FixedMessage.objects.filter(text=text).exists():
                raise forms.ValidationError(
                    "A fixed message with this text already exists"
                )

            # Update the cleaned data with stripped text
            self.cleaned_data["text"] = text

        return text

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes for better styling
        for field_name, field in self.fields.items():
            field.widget.attrs.update(
                {"class": "form-control", "aria-describedby": f"{field_name}-help"}
            )


class FixedMessageEditForm(forms.ModelForm):
    class Meta:
        model = FixedMessage
        fields = ["text"]

        widgets = {
            "text": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter updated fixed message text",
                    "maxlength": "255",
                    "required": True,
                    "autocomplete": "off",
                }
            )
        }

        labels = {
            "text": "Updated Message Text",
        }

        help_texts = {
            "text": "Enter the updated text for the fixed message (max 255 characters)",
        }

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes for better styling
        for field_name, field in self.fields.items():
            field.widget.attrs.update(
                {"class": "form-control", "aria-describedby": f"{field_name}-help"}
            )

    def clean_text(self):
        """
        Custom validation for the text field that excludes current instance
        """
        text = self.cleaned_data.get("text")
        if text:
            # Strip whitespace
            text = text.strip()

            # Check if text is not empty after stripping
            if not text:
                raise forms.ValidationError("Message text cannot be empty")

            # Check if another message with same text already exists (excluding current instance)
            if self.instance and self.instance.pk:
                existing_messages = FixedMessage.objects.filter(text=text).exclude(
                    pk=self.instance.pk
                )
            else:
                existing_messages = FixedMessage.objects.filter(text=text)

            if existing_messages.exists():
                raise forms.ValidationError(
                    "Another fixed message with this text already exists"
                )

            # Update the cleaned data with stripped text
            self.cleaned_data["text"] = text

        return text
