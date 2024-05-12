from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth.decorators import login_required

from authenticationApp.models import CustomUser
from supportCenterApp.models import SupportTicket, FeedbackModel
from .models import Department, LoginHistoryModel
from .forms import DepartmentForm
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
        return render(request, "adminDashboardApp/tabs/careers.html")

    else:
        return redirect("core:explore")


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
