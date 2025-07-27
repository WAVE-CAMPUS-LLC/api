from django import forms
from .models import AppVersion


class AppVersionForm(forms.ModelForm):
    """
    Form for creating and editing AppVersion instances.
    """

    class Meta:
        model = AppVersion
        fields = ["platform", "latest_version", "minimum_required_version"]
        widgets = {
            "platform": forms.Select(
                attrs={
                    "class": "form-control",
                    "required": True,
                }
            ),
            "latest_version": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., 1.0.0",
                    "required": True,
                    "maxlength": "20",
                }
            ),
            "minimum_required_version": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., 0.9.0",
                    "required": True,
                    "maxlength": "20",
                }
            ),
        }
        help_texts = {
            "platform": "Select the platform for this app version",
            "latest_version": "The latest version number available for this platform",
            "minimum_required_version": "The minimum version required for the app to function",
        }

    def clean_latest_version(self):
        """Validate latest version format."""
        latest_version = self.cleaned_data.get("latest_version")
        if latest_version:
            # Basic version format validation (x.y.z)
            import re

            if not re.match(r"^\d+\.\d+\.\d+$", latest_version):
                raise forms.ValidationError(
                    "Version must be in format x.y.z (e.g., 1.0.0)"
                )
        return latest_version

    def clean_minimum_required_version(self):
        """Validate minimum required version format."""
        minimum_version = self.cleaned_data.get("minimum_required_version")
        if minimum_version:
            # Basic version format validation (x.y.z)
            import re

            if not re.match(r"^\d+\.\d+\.\d+$", minimum_version):
                raise forms.ValidationError(
                    "Version must be in format x.y.z (e.g., 0.9.0)"
                )
        return minimum_version

    def clean(self):
        """Validate that latest version is greater than or equal to minimum required version."""
        cleaned_data = super().clean()
        latest_version = cleaned_data.get("latest_version")
        minimum_version = cleaned_data.get("minimum_required_version")

        if latest_version and minimum_version:
            try:
                from packaging import version

                latest = version.parse(latest_version)
                minimum = version.parse(minimum_version)

                if latest < minimum:
                    raise forms.ValidationError(
                        "Latest version cannot be less than minimum required version"
                    )
            except ImportError:
                # Fallback if packaging is not available
                pass

        return cleaned_data
