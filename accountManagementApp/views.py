from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import UpdateUserForm, UpdateProfileForm
from authenticationApp.models import CustomUser
from .models import UserProfile


# Create your views here.
@login_required(login_url="authentication:login")
def profileView(request):
    return render(request, "accountManagementApp/profileManagement.html")


@login_required(login_url="authentication:login")
def settingsView(request):
    user = request.user
    if "form_type" in request.POST:
        user_form = UpdateUserForm(request.POST, instance=request.user)
        profile_form = UpdateProfileForm(request.POST, instance=request.user)
        form_type = request.POST.get("form_type")

        if form_type == "personal-info":
            form = user_form
            if form.is_valid():
                print(form.errors)
                print("Personal Info form is valid.")
                form.save()
                return redirect("accountManagement:userSettings")
        elif form_type == "email-info":
            form = user_form
            if form.is_valid():
                print("Email Info form is valid.")
                form.save()
                return redirect("accountManagement:userSettings")
        elif form_type in "phone-info":
            form = user_form
            if form.is_valid():
                print("Phone Info form is valid.")
                form.save()
                return redirect("accountManagement:userSettings")
        elif form_type in "location-info":
            form = profile_form
            if form.is_valid():
                print("Location Info form is valid.")
                form.save()
                return redirect("accountManagement:userSettings")

    else:
        user = request.user
        profile = UserProfile.objects.get(user=user)
        user_form = UpdateUserForm(
            instance=user,
            initial={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phone_number": user.phone_number,
            },
        )
        profile_form = UpdateProfileForm(
            instance=profile,
            initial={
                "status": profile.status,
                "country": profile.country,
            },
        )
    return render(
        request,
        "accountManagementApp/profileSettings.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
            "user": user,
        },
    )
