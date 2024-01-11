from http.client import HTTPResponse
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import UpdateContactInfo, UpdatePersonalInfo, UpdateProfileForm
from authenticationApp.models import CustomUser
from .models import UserProfile


# Create your views here.
@login_required(login_url="authentication:login")
def profileView(request):
    return render(request, "accountManagementApp/profileManagement.html")


@login_required(login_url="authentication:login")
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
