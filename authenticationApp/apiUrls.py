from django.urls import path
from . import apiViews
from .apiViews import LogoutAPIView

app_name="authentication_api"


urlpatterns = [
    path("api_login/", apiViews.login_api, name="login"),
    path('get-csrf-token/', apiViews.get_csrf_token, name='get-csrf-token'),
    path('api_logout/', LogoutAPIView.as_view(), name='api-logout'),
]