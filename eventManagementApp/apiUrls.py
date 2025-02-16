from django.urls import path
from .apiViews import CreateEventAPIView, SaveEventProgressAPIView, host_portal

app_name = "eventManagementAPI"

urlpatterns = [
    path("create/", CreateEventAPIView.as_view(), name="create_event"),
    path(
        "save-progress/<uuid:eventId>/",
        SaveEventProgressAPIView.as_view(),
        name="save_event_progress",
    ),
    path("host_portal/", host_portal, name="host_portal"),
]