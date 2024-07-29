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
    path("<uuid:collegeId>/exit/", views.exitCollege, name="exit")
]
