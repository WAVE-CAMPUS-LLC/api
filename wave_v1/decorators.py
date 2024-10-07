from functools import wraps
from django.shortcuts import redirect, render
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Group



def admin_required(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.user.has_perms(
            [
                "adminDashboardApp.view_support_portal",
                "adminDashboardApp.view_users",
                "adminDashboardApp.manage_users",
                "adminDashboardApp.view_applications",
                "adminDashboardApp.manage_applications",
                "adminDashboardApp.view_departments",
                "adminDashboardApp.manage_departments",
                "adminDashboardApp.view_all_events",
                "adminDashboardApp.manage_all_events",
                "adminDashboardApp.view_support_tickets",
                "adminDashboardApp.manage_support_tickets",
            ]
        ):
            return view_func(request, *args, **kwargs)
        else:
            return redirect("core:index")

    return wrapped_view


def superAdmin_required(view_func):
    """
    Decorator for my views that checks if the user has the all permissions of a super admin.
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.user.has_perms(
            [
                "adminDashboardApp.view_profile_overview",
                "adminDashboardApp.view_account_settings",
                "adminDashboardApp.view_support_portal",
                "adminDashboardApp.view_users",
                "adminDashboardApp.manage_users",
                "adminDashboardApp.view_applications",
                "adminDashboardApp.manage_applications",
                "adminDashboardApp.view_departments",
                "adminDashboardApp.manage_departments",
                "adminDashboardApp.view_all_events",
                "adminDashboardApp.manage_all_events",
                "adminDashboardApp.view_support_tickets",
                "adminDashboardApp.manage_support_tickets",
                "adminDashboardApp.create_event",
                "adminDashboardApp.manage_host_event",
                "adminDashboardApp.view_host_event",
            ]
        ):
            return view_func(request, *args, **kwargs)
        else:
            return render(request, "extras/invalid/invalid.html")

    return wrapped_view


def check_suspension(view_func):
    """
    Decorator to check if user is suspended.
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_suspended and request.user.has_perm(
                "adminDashboardApp.user_suspension"
            ):
                return render(request, "extras/appControl/suspension.html")
        return view_func(request, *args, **kwargs)

    return wrapped_view


def support(view_func):
    def wrapped_view(request, *args, **kwargs):
        if request.user.has_perms(
            [
                "adminDashboardApp.view_support_tickets",
                "adminDashboardApp.manage_support_tickets",
            ]
        ):
            return view_func(request, *args, **kwargs)
        else:
            return render(request, "extras/invalid/invalid.html")

    return wrapped_view


def group_required(group_name):
    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                # Check if the user is in the specified group
                if Group.objects.filter(name=group_name, user=request.user).exists():
                    return view_func(request, *args, **kwargs)
            return render(request, "extras/invalid/invalid.html")

        return wrapped_view

    return decorator


def campusManagerRequired(group_name):
    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                # Check if the user is in the specified group
                if Group.objects.filter(name=group_name, user=request.user).exists():
                    return view_func(request, *args, **kwargs)
            return render(request, "extras/invalid/notAManager.html")

        return wrapped_view

    return decorator