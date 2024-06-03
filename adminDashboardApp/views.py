from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail

from authenticationApp.models import CustomUser
from supportCenterApp.models import SupportTicket, FeedbackModel
from careerApp.models import CareerRoleApplication
from eventManagementApp.models import HostApplication

from wave_v1 import settings
from .models import Department, CareerRole, LoginHistoryModel
from .forms import DepartmentForm, CareerRoleCreationForm
from wave_v1.decorators import admin_required


    
# Create your views here.
@login_required(login_url="authentication:login")
@admin_required
def adminPortalView(request):
    if request.user.is_superuser:
        return render(request, "adminDashboardApp/index.html")
    else:
        return redirect("core:explore")


@login_required(login_url="authentication:login")
@admin_required
def adminDashboardView(request):
    if request.user.is_superuser:
        return render(request, "adminDashboardApp/tabs/dashboard.html")

    else:
        return redirect("core:explore")


# Department Management
@login_required(login_url="authentication:login")
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
    if request.user.is_superuser:
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
    else:
        return redirect("core:explore")


@login_required(login_url="authentication:login")
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
    if request.user.is_superuser:
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
    else:
        return redirect("core:explore")


@login_required(login_url="authentication:login")
@admin_required
def adminApplicationsView(request):
    if request.user.is_superuser:
        hostApplications = HostApplication.objects.all()
        
        if request.method == "POST":
            action =request.POST.get("applicationAction")
            applicant_email = request.POST.get("applicantEmail")
            
            if action == "approve":
                sendHostApprovalEmail(applicant_email)
                return redirect("waveAdmin:applications")
            elif action == "deny":
                sendHostDenyEmail(applicant_email)
                return redirect("waveAdmin:applications")
        return render(request, "adminDashboardApp/tabs/applications.html", {'hostApps': hostApplications})
    
    else:
        return redirect("core:explore")
def sendHostApprovalEmail(applicantEmail):
    try:
        subject = "Congratulations, You are a WAVE. host! Start hosting your events now."
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
@admin_required
def adminEventsView(request):
    if request.user.is_superuser:
        return render(request, "adminDashboardApp/tabs/events.html")

    else:
        return redirect("core:explore")



@login_required(login_url="authentication:login")
@admin_required
def adminUsersView(request):
    if request.user.is_superuser:
        # Going into the CustomUser database which holds all the users and fetching them to be displayed.
        total_users = CustomUser.objects.all()
        return render(
            request, "adminDashboardApp/tabs/users.html", {"users": total_users}
        )
    else:
        return redirect("core:explore")



@login_required(login_url="authentication:login")
@admin_required
def adminUserDetailedView(request, user_id):
    if request.user.is_superuser:
        try:
            user_in_view = CustomUser.objects.get(user_id=user_id)
            login_history = LoginHistoryModel.objects.filter(user=user_in_view) 
        except:
            return HttpResponse(
                "User does not exist."
            )  # Replace this with a page that renders a 404 error. User does not exist.

        return render(
            request,
            "adminDashboardApp/tabs/users/user.html",
            {
                "user": user_in_view,
                "login_history": login_history,
            },
        )
    else:
        return redirect("core:explore")



@login_required(login_url="authentication:login")
@admin_required
def adminCareersView(request):
    if request.user.is_superuser:
        # Querying every single career role.
        all_career_roles = CareerRole.objects.all()
        return render(
            request,
            "adminDashboardApp/tabs/careers.html",
            {"career_roles": all_career_roles},
        )

    else:
        return redirect("core:explore")



@login_required(login_url="authentication:login")
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
    if request.user.is_superuser:
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
@admin_required
def adminFinanceView(request):
    if request.user.is_superuser:
        return render(request, "adminDashboardApp/tabs/financial.html")

    else:
        return redirect("core:explore")



@login_required(login_url="authentication:login")
@admin_required
def adminSupportView(request):
    if request.user.is_superuser:
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
    else:
        return redirect("core:explore")



@login_required(login_url="authentication:login")
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
    if request.user.is_superuser:
        all_feedback_offers = FeedbackModel.objects.all()
        feedback_count = FeedbackModel.objects.count()

        return render(
            request,
            "adminDashboardApp/tabs/feedback.html",
            {"feedback_offers": all_feedback_offers, "feedback_count": feedback_count},
        )

    else:
        return redirect("core:explore")