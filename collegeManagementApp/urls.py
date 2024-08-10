from django.urls import path
from . import views


app_name = "colleges"

urlpatterns = [
    path("", views.collegeHomeView, name="home"),
    path("find/", views.collegeCampusesView, name="find"),
    path("add/", views.addCollegeView, name="add"),
    path("<uuid:collegeId>/view/", views.viewCollegeInformation, name="info"),
    path("<uuid:collegeId>/join/", views.joinCollege, name="join"),
    path("<uuid:collegeId>/join/verify/", views.verifyJoinCollege, name="verify"),
    path("<uuid:collegeId>/exit/", views.exitCollege, name="exit"),
    path(
        "<uuid:collegeId>/view/organization/create/", views.createOrg, name="createOrg"
    ),
    path(
        "<uuid:collegeId>/view/organization/<uuid:orgId>/",
        views.viewOrganization,
        name="viewOrg",
    ),
    path(
        "<uuid:collegeId>/view/organization/<uuid:orgId>/join/",
        views.joinOrganization,
        name="joinOrg",
    ),
    path(
        "<uuid:collegeId>/view/organization/<uuid:orgId>/leave/",
        views.leaveOrganization,
        name="leaveOrg",
    ),
]
