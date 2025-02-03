from django.urls import path
from . import apiViews

app_name="authentication_api"


urlpatterns = [
    path("login/", apiViews.login, name="login"),
]