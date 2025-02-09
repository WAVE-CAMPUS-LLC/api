from django.urls import path
from . import apiViews

app_name="authentication_api"


urlpatterns = [
    path("api_login/", apiViews.login_api_view, name="login"),
]