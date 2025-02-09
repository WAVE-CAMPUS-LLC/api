from django.urls import path
from . import apiViews

app_name = "account_api"


urlpatterns = [
    path("profile/", apiViews.profile_api, name="profile_api"),
]