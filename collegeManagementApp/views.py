from django.shortcuts import get_object_or_404, render, redirect
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from wave_v1.decorators import check_suspension, member, verified, onboarded
from datetime import datetime, timedelta
from django.utils.timezone import now
from django.db.models import Q
from datetime import date


from .forms import (
    CollegeRequestForm,
    JoinCollegeForm,
    OrganizationForm,
    VerifyCollegeJoinForm,
    EditOrganizationForm,
)
from .models import (
    CollegeRequest,
    Membership,
    Organization,
    OrganizationMembership,
)

# TODO (Dave): for some reason the college management College model is not working properly. Using this for now.
from adminDashboardApp.models import College
from accountManagementApp.models import UserProfile
from eventManagementApp.models import Event, EventPrivacy


# Create your views here.
def collegeHomeView(request):
    pageName = "Colleges"
    random_colleges = College.objects.order_by("?")[:3]
    print(random_colleges)
    return render(
        request,
        "collegeManagementApp/home.html",
        {"pageName": pageName, "random_colleges": random_colleges},
    )


def collegeCampusesView(request):
    pageName = "Colleges"

    if request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest":
        query = request.GET.get("query", "")
        results = College.objects.filter(name__icontains=query)

        # Render each result using the template
        if results.exists():
            results_html = []
            for college in results:
                html = render_to_string(
                    "collegeManagementApp/extras/search-item.html", {"college": college}
                )
                results_html.append(html)
            return JsonResponse({"results_html": results_html, "no_results": False})
        else:
            no_results_html = render_to_string(
                "collegeManagementApp/extras/no-result.html"
            )
            return JsonResponse(
                {
                    "results_html": [],
                    "no_results": True,
                    "no_results_html": no_results_html,
                }
            )

    colleges = College.objects.all()

    # Counting the number of users in a college.
    college_members_info = []
    for college in colleges:
        member_count = UserProfile.objects.filter(college=college).count()
        organization_count = Organization.objects.filter(college=college).count()
        college_members_info.append(
            {
                "college": college,
                "member_count": member_count,
                "organization_count": organization_count,
            }
        )

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



def requestCollege(request):
    pageName = "Colleges"

    if request.method == "POST":
        collegeRequestForm = CollegeRequestForm(request.POST)

        if collegeRequestForm.is_valid():
            collegeRequestForm.save()
            messages.success(
                request,
                "Your request has been submitted. We will get back to you soon.",
            )
            return redirect("colleges:find")
    else:
        collegeRequestForm = CollegeRequestForm()

    return render(
        request,
        "collegeManagementApp/requestCollege.html",
        {
            "pageName": pageName,
            "collegeRequestForm": collegeRequestForm,
            "apiKey": settings.COLLEGE_LIST_API_KEY,
        },
    )


@login_required
@member
@verified
@check_suspension
def viewCollegeInformation(request, collegeId):
    pageName = "Colleges"

    college = get_object_or_404(College, collegeId=collegeId)

    user_profile = UserProfile.objects.filter(user=request.user).first()
    is_member = Membership.objects.filter(user=request.user, college=college).exists()

    members = UserProfile.objects.filter(college=college)
    organizations = Organization.objects.filter(college=college, status="Accepted")

    if not request.user.is_authenticated:
        # Restrict events with age restrictions for anonymous users
        age_filter = Q(age_restriction="")
    else:
        # For authenticated users, calculate age and apply restrictions
        user_age = request.user.age
        if user_age is None and request.user.birthday:
            today = date.today()
            user_age = (
                today.year
                - request.user.birthday.year
                - (
                    (today.month, today.day)
                    < (request.user.birthday.month, request.user.birthday.day)
                )
            )
            request.user.age = user_age
            request.user.save()

        age_filter = Q(age_restriction="")
        if user_age:
            if user_age >= 21:
                age_filter |= Q(age_restriction="21+")
            if user_age >= 18:
                age_filter |= Q(age_restriction="18+")

    events = (
        Event.objects.filter(
            display_event_on_college=True, host__user_profile__college=college
        )
        .filter(age_filter)
        .order_by("-date")
    )

    # Update to use new fields
    events_restricted_to_college = (
        Event.objects.filter(
            forCollegesDisplay=True,
            privacy_details__restricted_college=college,
            status="live",
        )
        .filter(age_filter)
        .order_by("-date")
    )

    display_events_on_college = (
        Event.objects.filter(
            forAllDisplay=True,
            host__user_profile__college=college,
            status="live",
        )
        .filter(age_filter)
        .order_by("-date")
    )

    events = (events_restricted_to_college | display_events_on_college).distinct()

    today = now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    weekly_events = (
        Event.objects.filter(
            date__range=[start_of_week, end_of_week],
            status="live",
            forAllDisplay=True,  # Changed from privacy="Discoverable"
            admin_status="active",
        )
        .filter(age_filter)
        .order_by("?")[:3]
    )

    return render(
        request,
        "collegeManagementApp/collegeInformation.html",
        {
            "pageName": pageName,
            "college": college,
            "collegeMembers": members,
            "user_profile": user_profile,
            "organizations": organizations,
            "events": events,
            "weekly_events": weekly_events,
            "is_member": is_member,
        },
    )


@login_required
@member
@verified
@check_suspension
def joinCollege(request, collegeId):
    pageName = "Colleges"
    college = get_object_or_404(College, collegeId=collegeId)

    if request.method == "POST":
        joinForm = JoinCollegeForm(request.POST, college=college)
        joinForm.user = request.user
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
                return redirect("colleges:join", collegeId=collegeId)

            return redirect("colleges:verify", collegeId=collegeId)
    else:
        joinForm = JoinCollegeForm(college=college)

    return render(
        request,
        "collegeManagementApp/joinCollege.html",
        {
            "joinForm": joinForm,
            "college": college,
            "pageName": pageName,
            "apiKey": settings.COLLEGE_LIST_API_KEY,
        },
    )


@login_required
@member
@verified
@check_suspension
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
                return redirect("colleges:find")
            else:
                messages.error(request, "Invalid verification code!")

    else:
        verifyForm = VerifyCollegeJoinForm()
    return render(
        request,
        "collegeManagementApp/verifyJoinCollege.html",
        {
            "verifyForm": verifyForm,
            "college": college,
            "pageName": pageName,
            "apiKey": settings.COLLEGE_LIST_API_KEY,
        },
    )


@login_required
@member
@verified
@check_suspension
def exitCollege(request, collegeId):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    college = get_object_or_404(College, collegeId=collegeId)

    try:
        collegeMembership = Membership.objects.get(user=request.user, college=college)
    except Membership.DoesNotExist:
        messages.error(request, "You aren't a member of this college.")
        return redirect("colleges:find")


    if user_profile.college and str(user_profile.college.collegeId) == str(collegeId):
        user_profile.college = None
        collegeMembership.delete()
        user_profile.save()
        messages.success(request, "You have successfully left the college.")
        print("College removed from user's profile.")
    else:
        messages.error(request, "You are not a member of this college.")
        print("User is not a member of the college or college ID mismatch.")

    return redirect("colleges:find")


@login_required
@member
@verified
@check_suspension
def createOrg(request, collegeId):
    pageName = "Colleges"
    college = get_object_or_404(College, collegeId=collegeId)

    if not request.user.is_authenticated:
        return render(
            request,
            "collegeManagementApp/extras/notAMemberOfCollege.html",
            {
                "college": college,
                "pageName": pageName,
                "apiKey": settings.COLLEGE_LIST_API_KEY,
            },
        )

    user_profile = UserProfile.objects.filter(user=request.user).first()

    if user_profile and user_profile.college != college:
        return render(
            request,
            "collegeManagementApp/extras/notAMemberOfCollege.html",
            {
                "college": college,
                "pageName": pageName,
                "apiKey": settings.COLLEGE_LIST_API_KEY,
            },
        )

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
            organization.status = "Pending"
            organization.save()
            OrganizationMembership.objects.create(
                user=request.user, organization=organization
            )

            return redirect("colleges:find")
    else:
        orgForm = OrganizationForm()
    return render(
        request,
        "collegeManagementApp/createCampusOrg.html",
        {"college": college, "orgForm": orgForm, "pageName": pageName},
    )


@login_required
@member
@verified
@check_suspension
def viewOrganization(request, collegeId, orgId):
    pageName = "Colleges"
    college = get_object_or_404(College, collegeId=collegeId)

    if not request.user.is_authenticated:
        return render(
            request,
            "collegeManagementApp/extras/notAMemberOfCollege.html",
            {
                "college": college,
                "pageName": pageName,
                "apiKey": settings.COLLEGE_LIST_API_KEY,
            },
        )

    user_profile = UserProfile.objects.filter(user=request.user).first()

    if user_profile and user_profile.college != college:
        return render(
            request,
            "collegeManagementApp/extras/notAMemberOfCollege.html",
            {
                "college": college,
                "pageName": pageName,
                "apiKey": settings.COLLEGE_LIST_API_KEY,
            },
        )

    if not Membership.objects.filter(user=request.user, college=college).exists():
        messages.error(
            request, "You must be a member of this college to create an organization."
        )
        return redirect("colleges:find")
    organization = get_object_or_404(Organization, orgId=orgId, college=college)

    is_owner = organization.created_by == user_profile.user

    is_member = OrganizationMembership.objects.filter(
        user=request.user, organization=organization
    ).exists()

    member_count = OrganizationMembership.objects.filter(
        organization=organization
    ).count()
    members = OrganizationMembership.objects.filter(
        organization=organization
    ).select_related("user")

    if not request.user.is_authenticated:
        # Restrict events with age restrictions for anonymous users
        age_filter = Q(age_restriction="")
    else:
        # For authenticated users, calculate age and apply restrictions
        user_age = request.user.age
        if user_age is None and request.user.birthday:
            today = date.today()
            user_age = (
                today.year
                - request.user.birthday.year
                - (
                    (today.month, today.day)
                    < (request.user.birthday.month, request.user.birthday.day)
                )
            )
            request.user.age = user_age
            request.user.save()

        age_filter = Q(age_restriction="")
        if user_age:
            if user_age >= 21:
                age_filter |= Q(age_restriction="21+")
            if user_age >= 18:
                age_filter |= Q(age_restriction="18+")

    # Get events restricted to this organization
    restricted_events = (
        Event.objects.filter(
            privacy="Private (Organization)",
            privacy_details__restricted_organization=organization,
        )
        .filter(age_filter)
        .order_by("-date")
    )

    org_privacy = organization.privacy
    org_owner = organization.created_by

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "kickMember":
            member_username = request.POST.get("leavingMemberUsername")
            member = UserProfile.objects.filter(user__username=member_username).first()
            if member:
                OrganizationMembership.objects.filter(
                    user=member.user, organization=organization
                ).delete()
                messages.success(
                    request,
                    f"{member.user.username} has been removed from the organization.",
                )

            elif not member:
                messages.error(request, "User not found.")

            else:
                messages.error(request, "An error occurred.", extra_tags="danger")

            return redirect("colleges:viewOrg", collegeId=collegeId, orgId=orgId)
        if action == "deleteOrg":
            all_memberships = OrganizationMembership.objects.filter(
                organization=organization
            )
            all_memberships.delete()

            events = Event.objects.filter(
                privacy="Private (Organization)",
                privacy_details__restricted_organization=organization,
            )
            events.delete()

            event_privacy = EventPrivacy.objects.filter(
                restricted_organization=organization
            )
            event_privacy.delete()

            organization.delete()
            messages.success(request, f"{organization.name} has been deleted.")
            return redirect("colleges:find")
        if action == "saveChanges":
            orgForm = EditOrganizationForm(
                request.POST, request.FILES, instance=organization
            )

            if orgForm.is_valid():
                org = orgForm.save(commit=False)

                if "logo" in request.FILES:
                    org.logo = request.FILES["logo"]

                org.save()

                messages.success(request, "Changes saved successfully.")
                return redirect("colleges:viewOrg", collegeId=collegeId, orgId=orgId)

    form = EditOrganizationForm(instance=organization)

    if org_privacy == "Private" and not is_member:
        return render(
            request,
            "collegeManagementApp/extras/privateOrg.html",
            {"pageName": pageName, "college": college, "organization": organization},
        )
    else:
        return render(
            request,
            "collegeManagementApp/organizations/viewOrg.html",
            {
                "pageName": pageName,
                "college": college,
                "organization": organization,
                "is_member": is_member,
                "member_count": member_count,
                "members": members,
                "events": restricted_events,
                "isOwner": is_owner,
                "orgOwner": org_owner,
                "form": form,
            },
        )


@login_required
@member
@verified
@check_suspension
def joinOrganization(request, collegeId, orgId):
    college = get_object_or_404(College, collegeId=collegeId)
    organization = get_object_or_404(Organization, orgId=orgId, college=college)

    if not OrganizationMembership.objects.filter(
        user=request.user, organization=organization
    ).exists():
        OrganizationMembership.objects.create(
            user=request.user, organization=organization
        )
        messages.success(request, f"You have successfully joined {organization.name}!")
    else:
        messages.warning(request, "You are already a member of this organization!")

    return redirect("colleges:viewOrg", collegeId=collegeId, orgId=orgId)


@login_required
@member
@verified
@check_suspension
def leaveOrganization(request, collegeId, orgId):
    college = get_object_or_404(College, collegeId=collegeId)
    organization = get_object_or_404(Organization, orgId=orgId, college=college)

    membership = OrganizationMembership.objects.filter(
        user=request.user, organization=organization
    ).first()

    if membership:
        membership.delete()
        messages.success(request, f"You have successfully left {organization.name}!")
    else:
        messages.warning(request, "You are not a member of this organization!")

    return redirect("colleges:viewOrg", collegeId=collegeId, orgId=orgId)
