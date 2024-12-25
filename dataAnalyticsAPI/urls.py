from django.urls import path
from . import views


app_name = "analyticsAPI"

urlpatterns = [
    path("analyticsApi/user/signups/", views.userSignups, name="userSignups"),
    
]