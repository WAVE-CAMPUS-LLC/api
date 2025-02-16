from django.urls import path
from .apiViews import CreateEventAPIView, SaveEventProgressAPIView, HostPortalView

app_name = "eventManagementAPI"

urlpatterns = [
    path("create/", CreateEventAPIView.as_view(), name="create_event"),
    path(
        "save-progress/<uuid:eventId>/",
        SaveEventProgressAPIView.as_view(),
        name="save_event_progress",
    ),
    path("portal/", HostPortalView.as_view(), name="host_portal"),
]