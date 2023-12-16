from django.urls import path
from . import views


app_name = "accountManagement"

urlpatterns = [
    path("profile/", views.userAccountView, name="userAccount"), 
]