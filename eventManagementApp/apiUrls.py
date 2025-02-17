from django.urls import path
from .apiViews import CreateEventAPIView, CreatePaidEventView, host_portal

app_name = "eventManagementAPI"

urlpatterns = [
    path("create/", CreateEventAPIView.as_view(), name="create_event"),
    path("host_portal/", host_portal, name="host_portal"),
    path("create_paid_event/", CreatePaidEventView.as_view(), name="create_paid_event"),
]