from django.urls import path
from . import views


app_name = "blog"

urlpatterns = [
    path("", views.blogHomeView, name="home"),
    path("create/", views.blogCreateView, name="createBlog"),
    path("<uuid:blogId>/", views.blogView, name="blogView"),  
]