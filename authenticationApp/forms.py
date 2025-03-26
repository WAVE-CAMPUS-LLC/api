import datetime
from datetime import datetime
from django import forms
from .models import CustomUser
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import (
    UserCreationForm,
    UserChangeForm,
    AuthenticationForm,
    PasswordResetForm,
)
from django.contrib import messages
from hcaptcha.fields import hCaptchaField


class CustomUserJoinForm(UserCreationForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)
    current_year = datetime.now().year
    birthday = forms.DateField(widget=forms.SelectDateWidget(years=range(1980, current_year + 1)))    
    captcha = hCaptchaField()

    class Meta:
        model = CustomUser
        fields = (
            "first_name",
            "last_name",
            "email",
            "username",
            "birthday",
            "password1",
            "password2",
            "captcha",
        )

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords do not match!")

        return password2

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("Email taken!")
        return email

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if CustomUser.objects.filter(username=username).exists():
            raise ValidationError("Username taken!")
        return username


    # In the defined function below, we loop through the first_name to see if it meets the set criteria.
    def clean_first_name(self):
        first_name = self.cleaned_data.get("first_name")
        if not all(
            char.isalpha() or char.isspace() or char == "-" for char in first_name
        ):
            raise ValidationError("Can contain only letters, spaces, or hyphens.")
        return first_name.strip()

    # In the defined function below, we loop through the first_name to see if it meets the set criteria.
    def clean_last_name(self):
        last_name = self.cleaned_data.get("last_name")
        if not all(
            char.isalpha() or char.isspace() or char == "-" for char in last_name
        ):
            raise ValidationError("Can contain only letters, spaces, or hyphens.")
        return last_name.strip()


    def save(self, commit=True):
        user = super().save(commit=False)
        

        if commit:
            user.save()

        return user



class MobileUserJoinForm(UserCreationForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)
    current_year = datetime.now().year
    birthday = forms.DateField(widget=forms.SelectDateWidget(years=range(1980, current_year + 1)))    

    class Meta:
        model = CustomUser
        fields = (
            "first_name",
            "last_name",
            "email",
            "username",
            "birthday",
            "password1",
            "password2",
        )

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords do not match!")

        return password2

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("Email taken!")
        return email

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if CustomUser.objects.filter(username=username).exists():
            raise ValidationError("Username taken!")
        return username


    # In the defined function below, we loop through the first_name to see if it meets the set criteria.
    def clean_first_name(self):
        first_name = self.cleaned_data.get("first_name")
        if not all(
            char.isalpha() or char.isspace() or char == "-" for char in first_name
        ):
            raise ValidationError("Can contain only letters, spaces, or hyphens.")
        return first_name.strip()

    # In the defined function below, we loop through the first_name to see if it meets the set criteria.
    def clean_last_name(self):
        last_name = self.cleaned_data.get("last_name")
        if not all(
            char.isalpha() or char.isspace() or char == "-" for char in last_name
        ):
            raise ValidationError("Can contain only letters, spaces, or hyphens.")
        return last_name.strip()


    def save(self, commit=True):
        user = super().save(commit=False)
        

        if commit:
            user.save()

        return user



class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = (
            "first_name",
            "last_name",
            "email",
            "username",
        )


class UserAuthenticationForm(forms.Form):
    identifier = forms.CharField(label="Email or Username")
    password = forms.CharField(label="Password", widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        identifier = cleaned_data.get("identifier")
        password = cleaned_data.get("password")

        if identifier and password:
            # Try authenticating by email
            user = CustomUser.objects.filter(email=identifier).first()
            if not user:
                # Try authenticating by username
                user = CustomUser.objects.filter(username=identifier).first()
            
            if not user:
                self.add_error("identifier", forms.ValidationError("Invalid credentials"))
            elif not user.check_password(password):
                self.add_error("password", forms.ValidationError("Incorrect password"))

        
        return cleaned_data

# Extend from Django's default password reset form and use it to build customized form.
class EmailPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label="Enter your email",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "off"}),
    )

    def clean_email(self):
        email = self.cleaned_data.get("email")

        try:
            CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise forms.ValidationError("Account does not exist.")
        return email


class NewPasswordForm(forms.Form):
    password = forms.CharField(label="New Password", widget=forms.PasswordInput)
    confirm_password = forms.CharField(
        label="Confirm Password", widget=forms.PasswordInput
    )

    def clean_passwords(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match")

        return cleaned_data
