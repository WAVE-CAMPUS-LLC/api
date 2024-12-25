from django.urls import path
from . import views


app_name = "dataAnalytics"

urlpatterns = [
    path("", views.analyticsHome, name="home"),
    path("user/signups/", views.userSignups, name="userSignups"),
    path("user/demographics/", views.userDemographics, name="userDemographics"),
    path("user-analytics/", views.userAnalytics, name="userAnalytics"),
    path("analytics/user/count/", views.user_count_api, name="userCountApi"),
]