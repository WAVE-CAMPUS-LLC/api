from http.client import HTTPResponse
from django.http import Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .forms import (
    UserProfileForm,
    UpdateContactInfo,
    UpdatePersonalInfo,
    UpdateProfileForm,
)
from .models import UserProfile

# Decorators to check user roles and permissions
from wave_v1.decorators import group_required, check_suspension
from blogApp.models import Blog

UserModel = get_user_model()


# Create your views here.
@login_required(login_url="authentication:login")
@check_suspension
@group_required("Member")
def profileView(request):
    userRequest = request.user
    blogItems = Blog.objects.filter(created_by=userRequest)
    userProfile = UserProfile.objects.get(user=userRequest)
    print(userProfile.profile_photo)
    
    return render(
        request,
        "accountManagementApp/profileOverview.html",
        {
            "blogItems": blogItems,
            "userRequest": userRequest,
            "userProfile": userProfile,
        },
    )
    

@login_required(login_url="authentication:login")
@check_suspension
@group_required("Member")
def profilePreferences(request):
    user = request.user
    profile = UserProfile.objects.get(user=user)
    profile_form = UserProfileForm(instance=profile)
    userModel = UserModel.objects.get(email=user.email)

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            userModel.user_preferences_completed = True
            form.save()
            return redirect("accountManagement:userAccount")

    return render(
        request,
        "accountManagementApp/extras/preferences.html",
        {"updateUserProfileForm": profile_form, "user": user},
    )


@login_required(login_url="authentication:login")
@check_suspension
@group_required("Member")
def settingsView(request):
    user = request.user
    personal_form = UpdatePersonalInfo(instance=user)
    profile = UserProfile.objects.get(user=user)
    contact_form = UpdateContactInfo(instance=user)
    profile_form = UpdateProfileForm(instance=profile)

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "personal-info":
            form = UpdatePersonalInfo(request.POST, instance=user)
            if form.is_valid():
                form.save()
        elif form_type == "email-info":
            form = UpdateContactInfo(request.POST, instance=user)
            if form.is_valid():
                form.save()
        elif form_type == "phone-info":
            form = UpdateContactInfo(request.POST, instance=user)
            if form.is_valid():
                form.save()
        elif form_type == "location-info":
            form = UpdateProfileForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
        else:
            return HttpResponseBadRequest("Invalid form type")

        return redirect("accountManagement:userSettings")

    return render(
        request,
        "accountManagementApp/profileSettings.html",
        {
            "personal_form": personal_form,
            "contact_form": contact_form,
            "profile_form": profile_form,
            "user": user,
            "phone_number": user.phone_number,
        },
    )


from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth import update_session_auth_hash


class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    template_name = "accountManagementApp/partials/passwordChange.html"
    success_message = "Password successfully changed!"

    def post(self, request, *args, **kwargs):
        # Call the original post method to handle password change logic
        result = super().post(request, *args, **kwargs)

        # If password change is successful, update the session
        if result.status_code == 302:  # Redirection status code
            update_session_auth_hash(request, request.user)  # type: ignore

        return result

    success_url = reverse_lazy("accountManagement:userAccount")
