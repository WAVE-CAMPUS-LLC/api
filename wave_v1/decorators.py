from functools import wraps
from django.shortcuts import redirect, render
from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        else:
            return redirect("core:index")

    return wrapped_view


def superAdmin_required(view_func):
    """
    Decorator for my views that checks if the user has the all permissions of a super admin.
    """

    def wrapped_view(request, *args, **kwargs):
        if request.user.has_perms(
            [
                "adminDashboardApp.view_users",
                "adminDashboardApp.manage_users",
                "adminDashboardApp.view_all_events",
                "adminDashboardApp.manage_all_events",
                "adminDashboardApp.view_support_tickets",
                "adminDashboardApp.manage_support_tickets",
                "adminDashboardApp.view_applications",
                "adminDashboardApp.manage_applications",
                "adminDashboardApp.view_departments",
                "adminDashboardApp.manage_departments",
            ]
        ):
            return view_func(request, *args, **kwargs)
        else:
            return render(request, "extras/invalid/invalid.html")

    return wrapped_view


def support(view_func):
    def wrapped_view(request, *args, **kwargs):
        if request.user.has_perms(
            [
                'adminDashboardApp.view_support_tickets',
                'adminDashboardApp.manage_support_tickets',
            ]
        ):
            return view_func(request, *args, **kwargs)
        else:
            return render(request, "extras/invalid/invalid.html")
    return wrapped_view

def member_required(view_func):
    def wrapped_view(request, *args, **kwargs):

        if request.user.has_perms(
            [
                "adminDashboardApp.view_profile_overview",
                "adminDashboardApp.view_account_settings",
                "adminDashboardApp.view_support_portal",
            ]
        ):
            return view_func(request, *args, **kwargs)
        else:
            return render(request, "extras/invalid/invalid.html")

    return wrapped_view
