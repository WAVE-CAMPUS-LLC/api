from django.urls import path
from . import views


app_name = "dataAnalytics"

urlpatterns = [
    # User Analytics
    path("", views.analyticsHome, name="home"),
    path("user/signups/", views.userSignups, name="userSignups"),
    path("user/logins/", views.userLogins, name="userLogins"),
    path("user/demographics/", views.userDemographics, name="userDemographics"),
    
    # College Analytics
    path("colleges/overview/", views.collegeOverview, name="collegeOverview"),
    path("colleges/membership/", views.collegeMembership, name="collegeMembership"),
    path("organization/overview/", views.organizationOverview, name="organizationOverview"),
    path("organization/membership/", views.organizationMembership, name="organizationMembership"),  
]