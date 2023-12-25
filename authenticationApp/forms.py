from django import forms
from .models import CustomUser
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import (
    UserCreationForm,
    UserChangeForm,
    AuthenticationForm,
)



class CustomUserJoinForm(UserCreationForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = (
            "first_name",
            "last_name",
            "email",
            "birthday",
            "gender",
            "phone_number",
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
            raise ValidationError("Email already in use.")
        return email
    
    # def clean(self):
    #     cleaned_data = super().clean()
    #     password2 = cleaned_data.get("password2")
    #     email = cleaned_data.get("email")

    #     if email and (email.lower() in password2.lower() or password2.lower() in email.lower()):
    #         raise ValidationError("Password similar to email.")

    #     return cleaned_data
    
    #In the defined function below, we loop through the first_name to see if it meets the set criteria.
    def clean_first_name(self):
        first_name = self.cleaned_data.get("first_name")
        if not all(char.isalpha() or char.isspace() or char == '-' for char in first_name):
            raise ValidationError("Can contain only letters, spaces, or hyphens.")
        return first_name.strip()
    
    #In the defined function below, we loop through the first_name to see if it meets the set criteria.
    def clean_last_name(self):
        last_name = self.cleaned_data.get("last_name")
        if not all(char.isalpha() or char.isspace() or char == '-' for char in last_name):
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
            "birthday",
            "gender",
            "phone_number",
        )


class UserAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("username", None)

    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Password", widget=forms.PasswordInput)

    # Checking to see if account exists at all using email address.
    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Account does not exist.")
        return email

    # Now checking and comparing the email address to the password stored in the system.
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        # If the email and password are inputed in, compare the input password and password stored in the database.
        if email and password:
            user = CustomUser.objects.filter(email=email).first()
            if user and not user.check_password(password):
                self.add_error("password", forms.ValidationError("Incorrect password."))

        return cleaned_data
