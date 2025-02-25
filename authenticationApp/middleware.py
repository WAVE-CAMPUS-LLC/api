from django.shortcuts import redirect
from django.urls import reverse

class RedirectAuthenticatedUsersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Force evaluation of request.user before processing the response.
        if request.user.is_authenticated:
            # Check if the user has completed onboarding.
            if not getattr(request.user, "email_verified", False):
                # Redirect new users to the onboarding page.
                if request.path not in [
                    reverse("authentication:logout"),
                    reverse("authentication:verifyEmail"),
                ]:
                    return redirect("authentication:verifyEmail")

            # Avoid accessing login or join pages when already logged in.
            restricted_urls = [
                reverse("authentication:login"),
                reverse("authentication:join"),
            ]
            if request.path in restricted_urls:
                next_url = request.GET.get("next", "accountManagement:userAccount")
                return redirect(next_url or "core:index")
        
        # Proceed with processing the request.
        response = self.get_response(request)
        return response
