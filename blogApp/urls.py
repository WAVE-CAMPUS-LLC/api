from django.urls import path
from . import views


app_name = "colleges"

urlpatterns = [
    path("blog/", views.blogHomeView, name="home"),
]