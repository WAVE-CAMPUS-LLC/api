from django.urls import path
from . import views

app_name = "accountManagement"

urlpatterns = [
    path("profile/", views.profileView, name="userAccount"),
    path("member/<str:username>/", views.memberView, name="memberProfile"),
    path("settings/", views.settingsView, name="userSettings"),
    path('change-password/', views.ChangePasswordView.as_view(), name="changePassword"),
]