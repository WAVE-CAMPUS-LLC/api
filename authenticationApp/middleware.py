from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone

# This is a middleware that prevents already authenticated users from accessing the login and join pages. 
class RedirectAuthenticatedUsersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Perform actions before sending the response
        if request.user.is_authenticated:
            restricted_urls = [reverse('authentication:login'), reverse('authentication:join')]
            if request.path in restricted_urls:
                next_url = request.GET.get("next", "accountManagement:userAccount")
                return redirect(next_url)
        return response

