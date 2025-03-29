from django.urls import path
from . import apiViews

app_name = "account_api"


urlpatterns = [
    path("profile/", apiViews.profile_api, name="profile_api"),
    path("profile/settings/", apiViews.settings_api, name="settings_api"),
    path("profile/favourites/", apiViews.favourited_events_api, name="favourite_events_api"),
    path("profile/payment-methods/", apiViews.get_payment_methods_api, name="get_payment_methods_api"),
    path("profile/college/", apiViews.get_user_college, name="get_user_college"),
    path("profile/delete/", apiViews.delete_account, name="delete_account"),
]