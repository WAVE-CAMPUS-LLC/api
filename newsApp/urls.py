from django.urls import path
from . import views

app_name = "newsApp"

urlpatterns = [
    path("newsroom/", views.frontpage, name="frontpage"),
]

