from django.http import JsonResponse
from authenticationApp.models import CustomUser


class UserAnalytics:
    def getUserCount(self):
        user_count =  CustomUser.objects.all().count()
        return JsonResponse({"user_count": user_count})


