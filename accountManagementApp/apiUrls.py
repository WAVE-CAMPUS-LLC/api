from django.urls import path
from . import apiViews

app_name = "account_api"


urlpatterns = [
    path("profile/", apiViews.profile_api, name="profile_api"),
    path("profile/settings/", apiViews.settings_api, name="settings_api"),
    path("profile/favourites/", apiViews.favourited_events_api, name="favourite_events_api"),
]