from django import forms
from .models import CustomUser
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import (
    UserCreationForm,
    UserChangeForm,
    AuthenticationForm,
    PasswordResetForm,
)


class CustomUserJoinForm(UserCreationForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)

    birthday_day = forms.IntegerField(
        label="Day", min_value=1, max_value=31, required=False
    )
    birthday_month = forms.IntegerField(
        label="Month", min_value=1, max_value=12, required=False
    )
    birthday_year = forms.IntegerField(
        label="Year", min_value=1950, max_value=2010, required=False
    )

    class Meta:
        model = CustomUser
        fields = (
            "first_name",
            "last_name",
            "email",
            "username",
            "phone_number",
            "birthday_day",
            "birthday_month",
            "birthday_year",
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

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if CustomUser.objects.filter(username=username).exists():
            raise ValidationError("Username already in use.")
        return username

    # def clean(self):
    #     cleaned_data = super().clean()
    #     password2 = cleaned_data.get("password2")
    #     email = cleaned_data.get("email")

    #     if email and (email.lower() in password2.lower() or password2.lower() in email.lower()):
    #         raise ValidationError("Password similar to email.")

    #     return cleaned_data

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

    def clean_birthday(self):
        cleaned_birthdayData = super().clean()
        birthday_day = cleaned_birthdayData.get("birthday_day")
        birthday_month = cleaned_birthdayData.get("birthday_month")
        birthday_year = cleaned_birthdayData.get("birthday_year")

        if birthday_day or birthday_month or birthday_year:
            if not all([birthday_day, birthday_month, birthday_year]):
                raise ValidationError("Enter a valid birthday.")

        return cleaned_birthdayData

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
    confirm_password = forms.CharField(label="Confirm New Password", widget=forms.PasswordInput)
    
    def clean_passwords(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        
        return cleaned_data
