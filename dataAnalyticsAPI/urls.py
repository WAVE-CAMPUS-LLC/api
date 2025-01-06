from django.urls import path
from . import views


app_name = "analyticsAPI"

urlpatterns = [
    # User Analytics
    path("analyticsApi/user/signups/", views.userSignups, name="userSignups"),
    path("analyticsApi/user/logins/", views.userLogins, name="userLogins"),
    path(
        "analyticsApi/user/demographics/",
        views.userDemographics,
        name="userDemographics",
    ),
    # College Analytics
    path(
        "analyticsApi/colleges/overview/", views.collegeOverview, name="collegeOverview"
    ),
    path(
        "analyticsApi/colleges/membership/",
        views.collegeMembership,
        name="collegeMembership",
    ),
    path('analyticsApi/organizations/overview/', views.organizationOverview, name='organizationOverview'),
    path('analyticsApi/organizations/membership/', views.organizationMembership, name='organizationMembership'),

    # Host Event Analytics
    path("analyticsApi/host/events/interaction/track/clicks/", views.trackEventClicks, name="trackEventClicks"),
    path("analyticsApi/host/events/interaction/track/views/", views.trackEventViews, name="trackEventViews"),
]
