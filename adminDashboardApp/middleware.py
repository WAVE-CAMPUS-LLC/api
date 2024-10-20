from django.utils.timezone import now
from .models import UserActivity

class UserRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            UserActivity.objects.create(
                user=request.user,
                action=f'visited {request.path}',
                timestamp=now()
            )
        response = self.get_response(request)
        return response
