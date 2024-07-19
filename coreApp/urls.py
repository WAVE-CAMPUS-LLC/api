from django.urls import path
from . import views


app_name = "core"

urlpatterns = [
    path("", views.indexView, name="index"), 
    path("explore/", views.exploreView, name="explore"),
    path("event/<uuid:eventId>/", views.eventDetailsView, name="eventDetails")
]