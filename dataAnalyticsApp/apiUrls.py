from django.urls import path
from . import apiViews

app_name = "dataAnalyticsAPI"

urlpatterns = [
    path("get_event_analytics/<uuid:eventId>/", apiViews.get_event_analytics, name="get_event_analytics"),
]