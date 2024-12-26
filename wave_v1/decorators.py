from functools import wraps
from django.shortcuts import redirect, render
from django.contrib.auth.models import Group


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


def member(view_func):
    """
    This decorator checks to see if the request user is a member.
    If they aren't a member, they will be redirected to the invalid page.
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            # Check if the user is in the group named "Member"
            if request.user.groups.filter(name="Member").exists():
                return view_func(request, *args, **kwargs)
        return render(request, "extras/invalid/invalid.html")

    return wrapped_view


def verified(view_func):
    """
    This decorator checks if the user has verified their email address.
    If the user has not verified their email address, they will be redirected to the email verification page.
    If the user has verified their email address, they will be able to access the view.
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if (
                request.user.email_verified
                and request.user.groups.filter(name="Verified").exists()
            ):
                return view_func(request, *args, **kwargs)
        return redirect("authentication:verifyEmail")

    return wrapped_view


def emailUnverified(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Check if the user is authenticated
        if request.user.is_authenticated:
            # Redirect if the email is already verified
            if request.user.email_verified:
                return redirect("accountManagement:userAccount")
        # Proceed to the view if email is not verified or user is unauthenticated
        return view_func(request, *args, **kwargs)

    return wrapped_view


def onboarded(view_func):
    """
    This decorator checks if the user has completed the onboarding process.
    If the user has not completed the onboarding process, they will be redirected to the onboarding page.
    If the user has completed the onboarding process, they will be able to access the view.
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if (
                request.user.is_onboarded
                and request.user.groups.filter(name="Onboarded").exists()
            ):
                return view_func(request, *args, **kwargs)
        return redirect("accountManagement:onboarding")

    return wrapped_view


def admin(view_func):
    """
    This decorator checks if the user is an admin.
    If the user is an admin, they will be able to access the view.
    If the user is not an admin, they will be redirected to the invalid page.
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.groups.filter(name="Admin").exists():
                return view_func(request, *args, **kwargs)
        return render(request, "extras/invalid/invalid.html")

    return wrapped_view


def superAdmin(view_func):
    """
    This decorator checks if the user is a super admin.
    If the user is a super admin, they will be able to access the view.
    If the user is not a super admin, they will be redirected to the invalid page.
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.groups.filter(name="Super Admin").exists():
                return view_func(request, *args, **kwargs)
        return render(request, "extras/invalid/invalid.html")

    return wrapped_view


def host(view_func):
    """
    This decorator checks if the user is a host.
    If the user is a host, they will be able to access the view.
    If the user is not a host, they will be redirected to the invalid page.
    """

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.groups.filter(name="Host").exists():
                return view_func(request, *args, **kwargs)
        return render(request, "extras/invalid/invalid.html")

    return wrapped_view


def campusManagerRequired(group_name):
    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                # Check if the user is in the specified group
                if request.user.groups.filter(name=group_name).exists():
                    return view_func(request, *args, **kwargs)
            return render(request, "extras/invalid/notAManager.html")

        return wrapped_view

    return decorator
