from django.urls import path
from . import views


app_name = "authentication"

urlpatterns = [
    path("join/", views.joinView, name="join"), 
    path("login/", views.loginView, name="login"),
    path("logout/", views.logoutView, name="logout")
]