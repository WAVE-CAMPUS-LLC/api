from django.urls import path
from .apiViews import createPaidEvent, getEventFormFields, host_portal

app_name = "eventManagementAPI"

urlpatterns = [
    path("host_portal/", host_portal, name="host_portal"),
    path("create_paid_event/", createPaidEvent, name="create_paid_event"),
    path("get_event_form_fields/", getEventFormFields, name="get_event_form_fields"),
]