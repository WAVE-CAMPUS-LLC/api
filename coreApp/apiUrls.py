from django.urls import path
from . import apiViews

urlpatterns = [
    path('explore-events/', apiViews.explore_events, name='api_explore_events'),
    path('load-more-events/', apiViews.load_more_events, name='api_load_more_events'),
    path('event/<uuid:eventId>/', apiViews.event_details, name='api_event_details'),
    path('event/<uuid:eventId>/toggle-favorite/', apiViews.toggle_favorite, name='api_toggle_favorite'),
    path('event/<uuid:eventId>/rsvp/', apiViews.handle_rsvp, name='api_handle_rsvp'),
    path('event/<uuid:eventId>/guests/', apiViews.event_guests, name='api_event_guests'),
]
