from django.urls import path
from . import apiViews

app_name="authentication_api"


urlpatterns = [
    path("api_login/", apiViews.LoginAPIView.as_view(), name="login"),
    path('get-csrf-token/', apiViews.get_csrf_token, name='get-csrf-token'),
]