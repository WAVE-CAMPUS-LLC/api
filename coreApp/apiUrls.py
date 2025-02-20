from django.urls import path
from . import apiViews

app_name = "core_api"

urlpatterns = [
    path("explore/", apiViews.explore_events, name="explore_events"),
    path("explore/load-more/", apiViews.load_more_events, name="load_more_events"),
    path("event/<str:eventId>/", apiViews.event_details, name="event_details"),
    path("event/<str:eventId>/favorite/", apiViews.toggle_favorite, name="favorite_event"),
    path("event/<str:eventId>/tickets/rsvp/", apiViews.handle_rsvp, name="rsvp_tickets"),
]
