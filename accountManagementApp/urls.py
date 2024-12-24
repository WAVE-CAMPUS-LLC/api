from django.urls import path
from . import views

app_name = "accountManagement"

urlpatterns = [
    path("profile/", views.profileView, name="userAccount"),
    path("profile/onboarding/", views.profilePreferences, name="onboarding"),
    path("profile=update/<str:username>/updatingprocess/", views.userProfileProcessing, name="updateProfileProcess"),
    path("settings/", views.settingsView, name="userSettings"),
    path('change-password/', views.ChangePasswordView.as_view(), name="changePassword"),
]