from django.urls import path
from . import views


app_name = "authentication"

urlpatterns = [
    path("join/", views.joinView, name="join"),
    path("verify/", views.startVerificationProcess, name="generateVerification"),
    path("verify/<str:token>/", views.verifyEmail, name="verify"), 
    path("login/", views.loginView, name="login"),
    path("logout/", views.logoutView, name="logout"),
    path("forgot/", views.forgotPasswordView, name="forgot"),
    path("password/reset/<uidb64>/oakbrothers/<token>/set/", views.setNewPassword, name="passwordReset"),
]