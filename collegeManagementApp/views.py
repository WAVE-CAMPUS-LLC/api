from django.shortcuts import get_object_or_404, render, redirect
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseRedirect

from .forms import CollegeForm, JoinCollegeForm, VerifyCollegeJoinForm
from .models import College
from accountManagementApp.models import UserProfile


# Create your views here.
def collegeHomeView(request):
    pageName = "Colleges"
    return render(request, "collegeManagementApp/home.html", {"pageName": pageName})


def collegeCampusesView(request):
    pageName = "Colleges"

    colleges = College.objects.all()
    user_profile = None
    if request.user.is_authenticated:
        user_profile = UserProfile.objects.filter(user=request.user).first()

    return render(
        request,
        "collegeManagementApp/campuses.html",
        {
            "pageName": pageName,
            "colleges": colleges,
            "user_profile": user_profile,
        },
    )


def addCollegeView(request):
    pageName = "Colleges"

    if request.method == "POST":
        collegeForm = CollegeForm(request.POST, request.FILES)

        if collegeForm.is_valid():
            collegeForm.save()

            return redirect("colleges:find")
    else:
        collegeForm = CollegeForm()
    return render(
        request,
        "collegeManagementApp/add.html",
        {"pageName": pageName, "collegeForm": collegeForm},
    )


def viewCollegeInformation(request, collegeId):
    pageName = "Colleges"

    college = get_object_or_404(College, collegeId=collegeId)
    members = UserProfile.objects.filter(college=college)

    user_profile = None
    if request.user.is_authenticated:
        user_profile = UserProfile.objects.filter(user=request.user).first()

    return render(
        request,
        "collegeManagementApp/collegeInformation.html",
        {
            "pageName": pageName,
            "college": college,
            "collegeMembers": members,
            "user_profile": user_profile,
        },
    )


@login_required
def joinCollege(request, collegeId):
    pageName = "Colleges"
    college = get_object_or_404(College, collegeId=collegeId)

    if request.method == "POST":
        joinForm = JoinCollegeForm(request.POST)
        if joinForm.is_valid():
            user = request.user
            email = joinForm.cleaned_data["email"]
            domain = email.split("@")[1]
            code = get_random_string(
                6, allowed_chars="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            )

            request.session["verification_code"] = code
            request.session["college_id"] = str(collegeId)
            request.session["user_email"] = email

            send_mail(
                "Verify your campus email",
                f"Your verification code is: {code}",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return redirect("colleges:verify", collegeId=collegeId)
    else:
        joinForm = JoinCollegeForm()

    return render(
        request,
        "collegeManagementApp/joinCollege.html",
        {"joinForm": joinForm, "college": college, "pageName": pageName},
    )


@login_required
def verifyJoinCollege(request, collegeId):
    pageName = "Colleges"
    college = get_object_or_404(College, collegeId=collegeId)

    if request.method == "POST":
        verifyForm = VerifyCollegeJoinForm(request.POST)
        if verifyForm.is_valid():
            code = verifyForm.cleaned_data["code"]
            if code == request.session.get("verification_code"):
                user_profile = get_object_or_404(UserProfile, user=request.user)
                user_profile.college = college
                user_profile.save()

                messages.success(
                    request,
                    f"You have successfully joined {college.name}. Enjoy all it has to offer!",
                )
                return redirect("core:index")
            else:
                messages.error(request, "Invalid verification code!")

    else:
        verifyForm = VerifyCollegeJoinForm()
    return render(
        request,
        "collegeManagementApp/verifyJoinCollege.html",
        {"verifyForm": verifyForm, "college": college, "pageName": pageName},
    )


@login_required
def exitCollege(request, collegeId):
    pageName = "Colleges"
    user_profile = get_object_or_404(UserProfile, user=request.user)

    print(f"User Profile: {user_profile}")
    print(f"User's College: {user_profile.college}")
    print(f"College ID in URL: {collegeId}")

    if user_profile.college and str(user_profile.college.collegeId) == str(collegeId):
        user_profile.college = None
        user_profile.save()
        messages.success(request, "You have successfully left the college.")
        print("College removed from user's profile.")
    else:
        messages.error(request, "You are not a member of this college.")
        print("User is not a member of the college or college ID mismatch.")

    return redirect("colleges:find")
