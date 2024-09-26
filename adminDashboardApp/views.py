from datetime import timedelta
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.contrib import messages
from django.utils.html import strip_tags
from django.db.models import Count
from django.core.mail import send_mail
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from django.core.signing import Signer
from django.utils import timezone
import uuid


from accountManagementApp.models import UserProfile
from authenticationApp.models import CustomUser
from supportCenterApp.models import SupportTicket, FeedbackModel
from careerApp.models import CareerRoleApplication
from eventManagementApp.models import HostApplication
from collegeManagementApp.models import (
    CollegeRequest,
    Organization,
    OrganizationMembership,
    Membership,
)
from campusManagerApp.models import CampusManagerInvite
from .models import College
from django.conf import settings
from .models import Department, CareerRole, LoginHistoryModel, Newsroom
from .forms import (
    CreateGroupForm,
    UpdateGroupForm,
    DepartmentForm,
    CareerRoleCreationForm,
    SuspendUserForm,
    CreateNewsForm,
    UpdateNewsTitleForm,
    UpdateNewsBodyForm,
    UpdateUrgencyLevelForm,
    UpdateNewsCategoryForm,
    UpdateHeaderImageForm,
    UpdateImageOneForm,
    UpdateImageTwoForm,
    UpdateImageThreeForm,
    CollegeForm,
)
from wave_v1.decorators import (
    admin_required,
    superAdmin_required,
    check_suspension,
)


# Create your views here.
@login_required(login_url="authentication:login")
@check_suspension
@admin_required
def adminPortalView(request):
    return render(request, "adminDashboardApp/index.html")


@login_required(login_url="authentication:login")
@check_suspension
@admin_required
def adminDashboardView(request):
    return render(request, "adminDashboardApp/tabs/dashboard.html")


# Department Management
@login_required(login_url="authentication:login")
@check_suspension
@admin_required
def adminDepartmentView(request):
    """
    The `adminDepartmentView` function checks if the user is a superuser, processes a form submission to
    save a new department, and renders a template with existing departments for an admin dashboard.

    :param request: The `request` parameter in the `adminDepartmentView` function is an object that
    contains information about the current HTTP request. It includes details such as the user making the
    request, the method used (GET, POST, etc.), any data sent with the request, and more. In this
    context,
    :return: The `adminDepartmentView` function is returning either a rendered template with a form and
    existing departments data, or it is redirecting to the "core:explore" URL depending on the user's
    permissions.
    """

    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("waveAdmin:departments")
    else:
        form = DepartmentForm()

    # Fetch all existing departments in order to pass them into the template
    departments = Department.objects.all()
    return render(
        request,
        "adminDashboardApp/tabs/departments.html",
        {"form": form, "departments": departments},
    )


@login_required(login_url="authentication:login")
@check_suspension
@admin_required
def adminDepartmentDetailedView(request, departmentID, department_name):
    """
    The function `adminDepartmentDetailedView` handles detailed view and management of department
    information for admin users, including creating, updating, and deleting career roles within a
    department.

    :param request: The code snippet you provided is a view function in Django that requires the user to
    be logged in and have admin privileges to access it. The function `adminDepartmentDetailedView`
    handles the detailed view of a department in an admin dashboard
    :param departmentID: The `departmentID` parameter is used to identify a specific department within
    the system. It is likely a unique identifier for each department, allowing the system to retrieve
    and manipulate data related to that specific department. In the provided code snippet, it is used to
    fetch the department object from the database using `
    :param department_name: The `department_name` parameter in the `adminDepartmentDetailedView`
    function represents the name of the department for which detailed information is being viewed. It is
    used in the URL pattern to uniquely identify the department along with the `departmentID`. This
    parameter is passed in the URL and helps in fetching the
    :return: The code snippet is returning either a rendered template
    "adminDashboardApp/tabs/departments/departmentDetails.html" with context data including the
    department, career roles, department form, and career role form, or it is redirecting to the
    "core:explore" URL if the user is not a superuser.
    """

    department = get_object_or_404(
        Department, departmentID=departmentID, name=department_name
    )
    careerRoles = CareerRole.objects.filter(department=department)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "delete":
            role_id = request.POST.get("role_id")
            careerRole_delete = get_object_or_404(CareerRole, roleID=role_id)
            careerRole_delete.delete()
            return redirect(
                "waveAdmin:departmentDetails",
                departmentID=departmentID,
                department_name=department_name,
            )

        departmentForm = DepartmentForm(request.POST, instance=department)
        careerRoleForm = CareerRoleCreationForm(request.POST)

        if departmentForm.is_valid():
            departmentForm.save()
            return redirect(
                "waveAdmin:departmentDetails",
                departmentID=departmentID,
                department_name=department_name,
            )

        elif careerRoleForm.is_valid():
            career_role = careerRoleForm.save(commit=False)
            career_role.department = department
            career_role.save()
            return redirect(
                "waveAdmin:departmentDetails",
                departmentID=departmentID,
                department_name=department_name,
            )
    else:
        departmentForm = DepartmentForm(instance=department)
        careerRoleForm = CareerRoleCreationForm()
    return render(
        request,
        "adminDashboardApp/tabs/departments/departmentDetails.html",
        {
            "department": department,
            "careerRoles": careerRoles,
            "departmentForm": departmentForm,
            "careerRoleForm": careerRoleForm,
        },
    )


@login_required(login_url="authentication:login")
@check_suspension
@admin_required
def adminApplicationsView(request):
    hostApplications = HostApplication.objects.all()

    if request.method == "POST":
        action = request.POST.get("applicationAction")
        applicant_email = request.POST.get("applicantEmail")

        if action == "approve":
            sendHostApprovalEmail(applicant_email)

            try:
                applicant = CustomUser.objects.get(email=applicant_email)
                host_group, created = Group.objects.get_or_create(name="Host")
                applicant.groups.add(host_group)
                applicant.save()

            except CustomUser.DoesNotExist:
                pass

            return redirect("waveAdmin:applications")

        elif action == "deny":
            sendHostDenyEmail(applicant_email)
            return redirect("waveAdmin:applications")
    return render(
        request,
        "adminDashboardApp/tabs/applications.html",
        {"hostApps": hostApplications},
    )


def sendHostApprovalEmail(applicantEmail):
    try:
        subject = (
            "Congratulations, You are a WAVE. host! Start hosting your events now."
        )
        emailMessageHtml = render_to_string(
            "emailTemplates/adminDashboardApp/applications/hostAppApproval.html", {}
        )
        plainMessage = strip_tags(emailMessageHtml)
        send_mail(
            subject, plainMessage, None, [applicantEmail], html_message=emailMessageHtml
        )
    except Exception as e:
        print(f"Error sending email to {applicantEmail}: {e}")


def sendHostDenyEmail(applicantEmail):
    try:
        subject = "Thank you for your application to be a host!"
        emailMessageHtml = render_to_string(
            "emailTemplates/adminDashboardApp/applications/hostAppDeny.html", {}
        )
        plainMessage = strip_tags(emailMessageHtml)
        send_mail(
            subject, plainMessage, None, [applicantEmail], html_message=emailMessageHtml
        )
    except Exception as e:
        print(f"Error sending email to {applicantEmail}: {e}")


@login_required(login_url="authentication:login")
@check_suspension
@admin_required
def adminEventsView(request):
    return render(request, "adminDashboardApp/tabs/events.html")


@login_required(login_url="authentication:login")
@check_suspension
@admin_required
def adminUsersView(request):
    # Going into the CustomUser database which holds all the users and fetching them to be displayed.
    total_users = CustomUser.objects.all()
    return render(request, "adminDashboardApp/tabs/users.html", {"users": total_users})


@login_required(login_url="authentication:login")
@check_suspension
@admin_required
def adminUserDetailedView(request, username):
    user_in_view = get_object_or_404(CustomUser, username=username)
    user_profile = UserProfile.objects.get(user=user_in_view)
    login_history = LoginHistoryModel.objects.filter(user=user_in_view)
    user_groups = user_in_view.groups.all()
    all_groups = Group.objects.all()
    available_groups = all_groups.difference(user_groups)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "suspend":
            suspend_form = SuspendUserForm(request.POST)
            if suspend_form.is_valid():
                hours = suspend_form.cleaned_data.get("hours", 0)
                user_in_view.suspend(hours)
                return redirect("waveAdmin:user-detailed", username=username)

        elif action == "allow":
            user_in_view.remove_suspension_OR_ban()
            return redirect("waveAdmin:user-detailed", username=username)

        group_id = request.POST.get("group_id")

        if group_id:
            group = get_object_or_404(Group, id=group_id)
            if "addRole" in request.POST:
                user_in_view.groups.add(group)
            elif "removeRole" in request.POST:
                user_in_view.groups.remove(group)
            return redirect("waveAdmin:user-detailed", username=username)

    else:
        suspend_form = SuspendUserForm()

    return render(
        request,
        "adminDashboardApp/tabs/users/user.html",
        {
            "user": user_in_view,
            "profile": user_profile,
            "login_history": login_history,
            "user_groups": user_groups,
            "available_groups": available_groups,
            "suspend_form": suspend_form,
        },
    )


@login_required(login_url="authentication:login")
@check_suspension
@admin_required
def adminRoleView(request):
    createGroup = CreateGroupForm()
    all_groups = Group.objects.all()
    all_permissions = Permission.objects.all()

    if request.method == "POST":
        action = request.POST.get("roleControlAction")
        group_id = request.POST.get("group_id")

        if action == "delete" and group_id:
            try:
                group = get_object_or_404(Group, id=group_id)
                group.delete()
                return redirect("waveAdmin:roles")
            except Group.DoesNotExist:
                pass

        if action == "edit" and group_id:
            group = get_object_or_404(Group, id=group_id)
            updateForm = UpdateGroupForm(request.POST, instance=group)
            if updateForm.is_valid():
                updateForm.save()
                return redirect("waveAdmin:roles")

        else:
            createGroup = CreateGroupForm(request.POST)
            if createGroup.is_valid():
                print(createGroup.cleaned_data)
                group = createGroup.save()
                print("Group created: ", group)
                print("Assigned permissions: ", group.permissions.all())

                return redirect("waveAdmin:roles")

    return render(
        request,
        "adminDashboardApp/tabs/roles.html",
        {
            "createGroupForm": createGroup,
            "allGroups": all_groups,
            "allPerms": all_permissions,
        },
    )


@login_required(login_url="authentication:login")
@check_suspension
@admin_required
def adminCareersView(request):
    # Querying every single career role.
    all_career_roles = CareerRole.objects.all()
    return render(
        request,
        "adminDashboardApp/tabs/careers.html",
        {"career_roles": all_career_roles},
    )


@login_required(login_url="authentication:login")
@check_suspension
@admin_required
def adminCareerDetailView(request, roleID):
    """
    The `adminCareerDetailView` function handles viewing and managing career details for admin users,
    including sending approval or denial emails to applicants.

    :param request: The `request` parameter in the `adminCareerDetailView` function is an HttpRequest
    object that represents the request made by a user to a Django view. It contains information about
    the request, such as the user making the request, any data sent with the request, and other metadata
    related to the request
    :param roleID: The `roleID` parameter in the `adminCareerDetailView` function is used to identify a
    specific career role based on its unique identifier. This identifier is used to query the details of
    the career role and retrieve related applications for that role
    :return: The `adminCareerDetailView` function is returning a rendered template with the context data
    `{"careerRoles_detail": career_role, "applications": applications}`. This template is used to
    display details of a specific career role along with its applications.
    """
    # Querying every single career role.
    career_role = get_object_or_404(CareerRole, roleID=roleID)

    applications = CareerRoleApplication.objects.filter(role=career_role)

    # Send email to applicant if they are denied or accepted.
    if request.method == "POST":
        action = request.POST.get("applicationAction")
        applicant_email = request.POST.get("applicantEmail")

        if action == "approve":
            sendApprovedApplicantEmail(applicant_email)
            return redirect("waveAdmin:careers")

        elif action == "deny":
            sendDeniedApplicantEmail(applicant_email)
            return redirect("waveAdmin:careers")
    return render(
        request,
        "adminDashboardApp/tabs/careers/careerDetails.html",
        {"careerRoles_detail": career_role, "applications": applications},
    )


def sendApprovedApplicantEmail(applicantEmail):
    try:
        subject = "Welcome to WAVE.!"
        emailMessageHtml = render_to_string(
            "emailTemplates/adminDashboardApp/careers/applicationApproved.html", {}
        )
        plainMessage = strip_tags(emailMessageHtml)
        send_mail(
            subject, plainMessage, None, [applicantEmail], html_message=emailMessageHtml
        )
    except Exception as e:
        print(f"Error sending email to {applicantEmail}: {e}")


def sendDeniedApplicantEmail(applicantEmail):
    try:
        subject = "Thank you for your application!"
        emailMessageHtml = render_to_string(
            "emailTemplates/adminDashboardApp/careers/applicationDenied.html", {}
        )
        plainMessage = strip_tags(emailMessageHtml)
        send_mail(
            subject, plainMessage, None, [applicantEmail], html_message=emailMessageHtml
        )
    except Exception as e:
        print(f"Error sending email to {applicantEmail}: {e}")


@login_required(login_url="authentication:login")
@check_suspension
@admin_required
def adminFinanceView(request):
    return render(request, "adminDashboardApp/tabs/financial.html")


@login_required(login_url="authentication:login")
@check_suspension
@admin_required
def adminSupportView(request):
    all_support_tickets = SupportTicket.objects.all()

    search_query = request.GET.get("support-ticket-search")
    if search_query:
        all_support_tickets = all_support_tickets.filter(
            ticket_id__icontains=search_query
        )

    active_support_tickets = all_support_tickets.filter(status="Open")
    inactive_support_tickets = all_support_tickets.filter(status="Closed")

    return render(
        request,
        "adminDashboardApp/tabs/support.html",
        {
            "active_tickets": active_support_tickets,
            "inactive_tickets": inactive_support_tickets,
            "search_query": search_query,
        },
    )


@login_required(login_url="authentication:login")
@check_suspension
@admin_required
def adminFeedbackView(request):
    """
    The `adminFeedbackView` function displays feedback offers for superusers and redirects
    non-superusers to the explore page.

    :param request: The `request` parameter in the `adminFeedbackView` function is an object that
    contains information about the current HTTP request. It includes details such as the user making the
    request, any data being sent with the request, and other metadata related to the request. In this
    context, the function is checking
    :return: The `adminFeedbackView` function is returning a response based on the user's permissions.
    If the user is a superuser, it retrieves all feedback offers from the `FeedbackModel`, counts the
    total number of feedback entries, and renders a template "adminDashboardApp/tabs/feedback.html" with
    the feedback offers and count as context data. If the user is not a superuser, it redirects
    """
    all_feedback_offers = FeedbackModel.objects.all()
    feedback_count = FeedbackModel.objects.count()

    return render(
        request,
        "adminDashboardApp/tabs/feedback.html",
        {"feedback_offers": all_feedback_offers, "feedback_count": feedback_count},
    )


@login_required
@check_suspension
@admin_required
def adminCollegeView(request):
    colleges = College.objects.annotate(member_count=Count("membership"))
    requestedColleges = CollegeRequest.objects.all()

    action = request.POST.get("eventAction")
    requestId = request.POST.get("requestId")

    if request.method == "POST":
        if action == "collegeCreated":
            if requestId:
                college_request = get_object_or_404(CollegeRequest, requestId=requestId)
                college_request.delete()
            return redirect("waveAdmin:colleges")

        collegeForm = CollegeForm(request.POST, request.FILES)
        college = collegeForm.save(commit=False)
        college.created_by = request.user
        try:
            user_profile = request.user.user_profile
            college.manager = user_profile
        except UserProfile.DoesNotExist:
            pass
        college.save()

    else:
        collegeForm = CollegeForm()
    return render(
        request,
        "adminDashboardApp/tabs/colleges.html",
        {
            "colleges": colleges,
            "collegeForm": collegeForm,
            "requestedColleges": requestedColleges,
        },
    )


@login_required
@check_suspension
@admin_required
def adminCollegeDetailView(request, collegeId):
    college = get_object_or_404(College, collegeId=collegeId)

    action = request.POST.get("eventAction")

    if request.method == "POST":
        email = request.POST.get("inviteEmail")

        if email:
            try:
                send_invite(email, college)
                messages.success(request, "Invite sent successfully")
            except Exception as e:
                messages.error(request, f"Error sending invite: {str(e)}")
        else:
            messages.error(request, "Please provide an email address")

        if action == "removeManager":
            manager_email = request.POST.get("managerEmail")
            if manager_email:
                try:
                    manager = get_object_or_404(CustomUser, email=manager_email)
                    college.managers.remove(manager)

                    invite = CampusManagerInvite.objects.filter(
                        email=manager_email, college=college, accepted=True
                    ).first()

                    if invite:
                        invite.delete()
                    messages.success(
                        request,
                        f"{manager.username} has been removed from managing the college.",
                    )
                except Exception as e:
                    messages.error(request, f"Error removing manager: {str(e)}")
            else:
                messages.error(request, "No manager email provided.")
        return redirect("waveAdmin:collegeDetail", collegeId=collegeId)

    return render(
        request,
        "adminDashboardApp/tabs/colleges/collegeInfo.html",
        {"college": college},
    )


def send_invite(email, college):
    """
    The function `send_invite` sends an invitation email to a user to become a Campus Manager at a
    specific college, handling existing invites and generating a unique invite link.
    
    :param email: The `email` parameter in the `send_invite` function is the email address of the person
    to whom the invitation will be sent
    :param college: The `college` parameter in the `send_invite` function is likely an object
    representing a college in your system. It seems to be used to associate the invite with a specific
    college when creating a new invite and when generating the invite link
    """
    existing_invite = CampusManagerInvite.objects.filter(
        email=email, college=college
    ).first()

    if existing_invite:
        if existing_invite.accepted:
            raise Exception(f"An invite has already been accepted by {email}.")
        else:
            existing_invite.delete()

    new_invite = CampusManagerInvite.objects.create(
        email=email,
        college=college,
        token=uuid.uuid4(),
        invited_at=timezone.now(),
    )

    invite_link = f'{settings.SITE_URL}{reverse("campusManager:accept_invite", kwargs={"token": new_invite.token, "collegeId": college.collegeId})}'

    send_mail(
        "You have been invited to be a Campus Manager",
        f"Click the link to accept: {invite_link}",
        "admin@waveapp.com",
        [email],
        fail_silently=False,
    )


@login_required
@check_suspension
@admin_required
def adminCollegeOrgsView(request):
    return render(request, "adminDashboardApp/tabs/organizations.html")


@login_required
@check_suspension
@admin_required
def adminNewsRoomView(request):
    news = Newsroom.objects.all()
    return render(request, "adminDashboardApp/tabs/newsroom.html", {"news": news})


@login_required
@check_suspension
@admin_required
def adminCreateNewsView(request):
    """
    This Python function handles the creation of news articles by processing form data and saving it to
    the database.
    
    :param request: The `request` parameter in the `adminCreateNewsView` function is an HttpRequest
    object that represents the current HTTP request. It contains information about the request made by
    the client, such as the request method (GET, POST, etc.), request data, user session information,
    and more. In this
    :return: The `adminCreateNewsView` function returns a rendered HTML template named "createNews.html"
    located in the "adminDashboardApp/tabs/newsroom" directory. The template is rendered with the
    `createNewsForm` context variable, which contains the form for creating news.
    """
    createNewsForm = CreateNewsForm(request.POST, request.FILES)
    if request.method == "POST":
        if createNewsForm.is_valid():
            news_instance = createNewsForm.save(commit=False)
            news_instance.created_by = request.user
            news_instance.save()
            return redirect("waveAdmin:newsroom")

        else:
            print(createNewsForm.errors)

    else:
        createNewsForm = CreateNewsForm()
    return render(
        request,
        "adminDashboardApp/tabs/newsroom/createNews.html",
        {"createNewsForm": createNewsForm},
    )


@login_required
@check_suspension
@admin_required
def adminEditNewsView(request, newsId):
    """
    This function is likely used to display a view for editing news articles by an admin.
    
    :param request: The `request` parameter in the `adminEditNewsView` function is typically an
    HttpRequest object that represents the current request from the user. It contains information about
    the request, such as the user's session, any data submitted through forms, and other metadata
    related to the request. This parameter allows the
    :param newsId: The `newsId` parameter in the `adminEditNewsView` function likely refers to the
    unique identifier of the news article that the function is intended to edit. This parameter allows
    the function to identify which specific news article is being edited within the administrative
    interface
    """
    newsItem = get_object_or_404(Newsroom, newsId=newsId)

    if request.method == "POST":
        field = request.POST.get("field")
        action = request.POST.get("eventAction")

        if action == "deleteNews":
            newsItem.delete()
            return redirect("waveAdmin:newsroom")

        if field == "title-info":
            titleFieldForm = UpdateNewsTitleForm(request.POST, instance=newsItem)
            if titleFieldForm.is_valid():
                titleFieldForm.save()

        elif field == "body-info":
            bodyFieldForm = UpdateNewsBodyForm(request.POST, instance=newsItem)
            if bodyFieldForm.is_valid():
                bodyFieldForm.save()

        elif field == "urgency-info":
            urgencyFieldForm = UpdateUrgencyLevelForm(request.POST, instance=newsItem)
            if urgencyFieldForm.is_valid():
                urgencyFieldForm.save()

        elif field == "newsCategory-info":
            newsCategoryForm = UpdateNewsCategoryForm(request.POST, instance=newsItem)
            if newsCategoryForm.is_valid():
                newsCategoryForm.save()

        elif field == "headerImage-info":
            headerImageForm = UpdateHeaderImageForm(
                request.POST, request.FILES, instance=newsItem
            )
            if headerImageForm.is_valid():
                headerImageForm.save()

        elif field == "imageOne-info":
            imageOneForm = UpdateImageOneForm(
                request.POST, request.FILES, instance=newsItem
            )
            if imageOneForm.is_valid():
                imageOneForm.save()

        elif field == "imageTwo-info":
            imageTwoForm = UpdateImageTwoForm(
                request.POST, request.FILES, instance=newsItem
            )
            if imageTwoForm.is_valid():
                imageTwoForm.save()

        elif field == "imageThree-info":
            imageThreeForm = UpdateImageThreeForm(
                request.POST, request.FILES, instance=newsItem
            )
            if imageThreeForm.is_valid():
                imageThreeForm.save()

        else:
            return HttpResponseBadRequest("Invalid form type")

        return redirect("waveAdmin:newsroom")

    else:
        titleFieldForm = UpdateNewsTitleForm()
        bodyFieldForm = UpdateNewsBodyForm()
        urgencyFieldForm = UpdateUrgencyLevelForm()
        newsCategoryForm = UpdateNewsCategoryForm()
        headerImageForm = UpdateHeaderImageForm()
        imageOneForm = UpdateImageOneForm()
        imageTwoForm = UpdateImageTwoForm()
        imageThreeForm = UpdateImageThreeForm()

    return render(
        request,
        "adminDashboardApp/tabs/newsroom/editNews.html",
        {
            "newsItem": newsItem,
            "titleFieldForm": titleFieldForm,
            "bodyFieldForm": bodyFieldForm,
            "urgencyFieldForm": urgencyFieldForm,
            "newsCategoryForm": newsCategoryForm,
            "headerImageForm": headerImageForm,
            "imageOneForm": imageOneForm,
            "imageTwoForm": imageTwoForm,
            "imageThreeForm": imageThreeForm,
        },
    )
