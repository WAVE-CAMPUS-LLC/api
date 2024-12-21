from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone


# This is a middleware that prevents already authenticated users from accessing the login and join pages.
# The `RedirectAuthenticatedUsersMiddleware` class redirects authenticated users from specific
# restricted URLs to a specified next URL or the index page.
class RedirectAuthenticatedUsersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Perform actions before sending the response
        if request.user.is_authenticated:
            # Check if the user has completed onboarding
            if not getattr(request.user, "is_onboarded", False):
                # Redirect new users to the onboarding page
                if request.path not in [
                    reverse("authentication:logout"),
                    reverse("authentication:onboarding"),
                ]:
                    return redirect("authentication:onboarding")

            # Avoid accessing login or join pages when already logged in
            restricted_urls = [
                reverse("authentication:login"),
                reverse("authentication:join"),
            ]
            if request.path in restricted_urls:
                next_url = request.GET.get("next", "accountManagement:userAccount")
                return redirect(next_url or "core:index")
        return response
