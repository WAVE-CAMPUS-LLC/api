from django.urls import path
from . import views

app_name = "careers"

urlpatterns = [
    path("careers/", views.careerHomeApp, name="home")
]
