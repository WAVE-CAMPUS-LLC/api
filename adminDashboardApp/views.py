from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail

from authenticationApp.models import CustomUser
from supportCenterApp.models import SupportTicket, FeedbackModel
from careerApp.models import CareerRoleApplication
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
