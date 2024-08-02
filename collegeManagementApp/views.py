from django.shortcuts import get_object_or_404, render, redirect
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseRedirect

from .forms import CollegeForm, JoinCollegeForm, OrganizationForm, VerifyCollegeJoinForm
from .models import College, Membership, Organization
from accountManagementApp.models import UserProfile


# Create your views here.
def collegeHomeView(request):
    pageName = "Colleges"
    return render(request, "collegeManagementApp/home.html", {"pageName": pageName})


def collegeCampusesView(request):
    pageName = "Colleges"

    colleges = College.objects.all()

    # Counting the number of users in a college.
    college_members_info = []
    for college in colleges:
        member_count = UserProfile.objects.filter(college=college).count()
        college_members_info.append({"college": college, "member_count": member_count})

    user_profile = None
    if request.user.is_authenticated:
        user_profile = UserProfile.objects.filter(user=request.user).first()

    return render(
        request,
        "collegeManagementApp/campuses.html",
        {
            "pageName": pageName,
            "college_members_info": college_members_info,
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
    organizations = Organization.objects.filter(college=college)

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
            "organizations": organizations,
        },
    )


@login_required
def joinCollege(request, collegeId):
    pageName = "Colleges"
    college = get_object_or_404(College, collegeId=collegeId)

    if request.method == "POST":
        joinForm = JoinCollegeForm(request.POST, college=college)
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

            try:
                send_mail(
                    "Verify your campus email",
                    f"Your verification code is: {code}",
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                print(f"Verification email sent to {email}")
            except Exception as e:
                print(f"Error sending email: {e}")

            return redirect("colleges:verify", collegeId=collegeId)
    else:
        joinForm = JoinCollegeForm(college=college)

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
                Membership.objects.get_or_create(user=request.user, college=college)

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
    user_profile = get_object_or_404(UserProfile, user=request.user)
    college = get_object_or_404(College, collegeId=collegeId)

    print(f"User Profile: {user_profile}")
    print(f"User's College: {user_profile.college}")
    print(f"College ID in URL: {collegeId}")

    if not Membership.objects.filter(user=request.user, college=college).exists():
        messages.error(request, "You aren't a member.")
        return redirect("colleges:find")

    if user_profile.college and str(user_profile.college.collegeId) == str(collegeId):
        user_profile.college = None
        user_profile.save()
        messages.success(request, "You have successfully left the college.")
        print("College removed from user's profile.")
    else:
        messages.error(request, "You are not a member of this college.")
        print("User is not a member of the college or college ID mismatch.")

    return redirect("colleges:find")


@login_required
def createOrg(request, collegeId):
    pageName = "Colleges"
    college = get_object_or_404(College, collegeId=collegeId)

    if not Membership.objects.filter(user=request.user, college=college).exists():
        messages.error(
            request, "You must be a member of this college to create an organization."
        )
        return redirect("colleges:find")

    if request.method == "POST":
        orgForm = OrganizationForm(request.POST, request.FILES)

        if orgForm.is_valid():
            organization = orgForm.save(commit=False)
            organization.college = college
            organization.created_by = request.user
            organization.save()

            return redirect("colleges:find")
    else:
        orgForm = OrganizationForm()
    return render(
        request,
        "collegeManagementApp/createCampusOrg.html",
        {"college": college, "orgForm": orgForm, "pageName": pageName},
    )


@login_required
def viewOrganization(request, collegeId, orgId):
    pageName = "Colleges"
    college = get_object_or_404(College, collegeId=collegeId)
    organization = get_object_or_404(Organization, orgId=orgId, college=college)

    return render(
        request,
        "collegeManagementApp/organizations/viewOrg.html",
        {"pageName": pageName, "college": college, "organization": organization},
    )
