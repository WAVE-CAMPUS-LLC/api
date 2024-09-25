from django.urls import path
from . import views

app_name = "campusManager"

urlpatterns = [
    path("dashboard/", views.managerDashboardView, name="dashboard"),
    path("invite/accept/<str:token>/<str:collegeId>/", views.accept_invite, name="accept_invite"),
]
