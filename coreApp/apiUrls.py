from django.urls import path
from . import apiViews

app_name = "core_api"

urlpatterns = [
    path("explore/", apiViews.explore_events, name="explore_events"),
    path("event/<str:eventId>/", apiViews.event_details, name="event_details"),
    path(
        "event/<str:eventId>/favorite/", apiViews.toggle_favorite, name="favorite_event"
    ),
    path(
        "event/<str:eventId>/tickets/rsvp/", apiViews.handle_rsvp, name="rsvp_tickets"
    ),
    path(
        "event/<uuid:eventId>/guests/", apiViews.event_guests, name="api_event_guests"
    ),
]
