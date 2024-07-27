from django.urls import path
from . import views


app_name = "colleges"

urlpatterns = [
    path("", views.collegeHomeView, name="home"),
    path("find/", views.collegeCampusesView, name="find"),
    path("add/", views.addCollegeView, name="add"),
    path("<uuid:collegeId>/view/", views.viewCollegeInformation, name="info"),
]
