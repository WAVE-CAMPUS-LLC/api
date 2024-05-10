from django.shortcuts import redirect
from django.urls import reverse

class RedirectAuthenticatedUsersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Perform actions before sending the response
        if request.user.is_authenticated:
            restricted_urls = [reverse('authentication:login'), reverse('authentication:join')]
            if request.path in restricted_urls:
                return redirect("accountManagement:userAccount")
        return response
