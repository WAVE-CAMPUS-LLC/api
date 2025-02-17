from django.urls import path
from .apiViews import CreateEventAPIView, createPaidEvent, getEventFormFields, host_portal

app_name = "eventManagementAPI"

urlpatterns = [
    path("create/", CreateEventAPIView.as_view(), name="create_event"),
    path("host_portal/", host_portal, name="host_portal"),
    path("create_paid_event/", createPaidEvent, name="create_paid_event"),
    path("get_event_form_fields/", getEventFormFields, name="get_event_form_fields"),
]