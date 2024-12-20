from django.urls import path
from . import views

app_name = "campusManager"

urlpatterns = [
    path("dashboard/", views.managerDashboardView, name="dashboard"),
    path("campus/<uuid:collegeId>/", views.managedCampusView, name="campus"),
    path("invite/accept/<str:token>/<str:collegeId>/", views.accept_invite, name="accept_invite"),
    path('colleges/<uuid:collegeId>/info/', views.college_detail_view, name='college_detail'),
]
