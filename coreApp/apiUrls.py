from django.urls import path
from . import apiViews

app_name = "core_api"

urlpatterns = [
    path("explore/", apiViews.explore_events, name="explore_events"),
    path("explore/load-more/", apiViews.load_more_events, name="load_more_events"),
    path("event/<int:eventId>/", apiViews.event_details, name="event_details"),
]
