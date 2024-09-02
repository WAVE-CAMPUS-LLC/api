from django.urls import path
from . import views

app_name = "newsroom"


urlpatterns = [
    path("newsroom/", views.newsroomView, name="home"), 
    path("news/<uuid:newsId>/", views.newsView, name="news"),  
]
