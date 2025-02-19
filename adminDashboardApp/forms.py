from django import forms
from django.contrib.auth.models import Permission, Group
from authenticationApp.models import CustomUser
from .models import Department, CareerRole, Newsroom, College
from django.utils.translation import gettext_lazy as translate


class CreateGroupForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    role_color = forms.CharField(
        label="Role Color",
        max_length=7,
        required=True,
        widget=forms.TextInput(attrs={"type": "color"}),
    )

    class Meta:
        model = Group
        fields = [
            "name",
            "permissions",
            "role_color",
        ]

    def save(self, commit=True):
        group = super().save(commit=False)
        if commit:
            group.save()
            group.permissions.set(self.cleaned_data["permissions"])
            group.role_color = self.cleaned_data["role_color"]
            group.save()
        return group


class UpdateGroupForm(forms.ModelForm):
    name = forms.CharField(
        max_length=150, required=False, help_text="Name", label="Name"
    )
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Permissions",
        label="Permissions",
    )
    role_color = forms.CharField(
        max_length=7,
        required=True,
        widget=forms.TextInput(attrs={"type": "color"}),
        help_text="Role Color",
        label="Role Color",
    )

    class Meta:
        model = Group
        fields = [
            "name",
            "permissions",
            "role_color",
        ]


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = [
            "name",
            "lead_name",
            "lead_email",
            "capacity",
            "location",
            "description",
        ]


class CareerRoleCreationForm(forms.ModelForm):
    class Meta:
        model = CareerRole
        fields = [
            "roleTitle",
            "roleDescription",
            "roleExpectations",
            "roleRequirements",
            "roleLocation",
            "roleType",
            "advertisementLength",
            "roleCapacity",
        ]


class SuspendUserForm(forms.Form):
    hours = forms.IntegerField(
        label=translate("Hours"), min_value=0, max_value=23, initial=0
    )


class CreateNewsForm(forms.ModelForm):
    class Meta:
        model = Newsroom
        fields = [
            "title",
            "newsCategory",
            "body",
            "headerImage",
            "imageOne",
            "imageTwo",
            "imageThree",
            "urgencyLevel",
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


class UpdateNewsTitleForm(forms.ModelForm):
    class Meta:
        model = Newsroom
        fields = [
            "title",
        ]


class UpdateNewsBodyForm(forms.ModelForm):
    class Meta:
        model = Newsroom
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


class UpdateUrgencyLevelForm(forms.ModelForm):
    class Meta:
        model = Newsroom
        fields = [
            "urgencyLevel",
        ]


class UpdateNewsCategoryForm(forms.ModelForm):
    class Meta:
        model = Newsroom
        fields = [
            "newsCategory",
        ]


class UpdateHeaderImageForm(forms.ModelForm):
    class Meta:
        model = Newsroom
        fields = [
            "headerImage",
        ]


class UpdateImageOneForm(forms.ModelForm):
    class Meta:
        model = Newsroom
        fields = [
            "imageOne",
        ]


class UpdateImageTwoForm(forms.ModelForm):
    class Meta:
        model = Newsroom
        fields = [
            "imageTwo",
        ]


class UpdateImageThreeForm(forms.ModelForm):
    class Meta:
        model = Newsroom
        fields = [
            "imageThree",
        ]


class CollegeForm(forms.ModelForm):
    class Meta:
        model = College
        fields = [
            "name",
            "address",
            "city",
            "state",
            "zip_code",
            "country",
            "logo",
            "campus_image",
            "motto",
            "contact_website",
        ]

        widgets = {"state": forms.Select(), "country": forms.Select()}


class EditCollegeForm(forms.ModelForm):
    class Meta:
        model = College
        fields = [
            "name",
            "address",
            "city",
            "state",
            "zip_code",
            "country",
            "logo",
            "campus_image",
            "motto",
            "contact_website",
        ]

        widgets = {
            "state": forms.Select(),
            "country": forms.Select(),
            "logo": forms.ClearableFileInput(
                attrs={
                    "class": "editInput hidden w-full appearance-none h-full p-4 py-3 font-Wanted-Variable text-Semi-Medium text-black border rounded-xl focus:ring-0 focus:none placeholder:text-[#00000076] placeholder:font-Wanted-Regular"
                }
            ),
            "campus_image": forms.ClearableFileInput(
                attrs={
                    "class": "editInput hidden w-full appearance-none h-full p-4 py-3 font-Wanted-Variable text-Semi-Medium text-black border rounded-xl focus:ring-0 focus:none placeholder:text-[#00000076] placeholder:font-Wanted-Regular"
                }
            ),
        }
