from django.urls import path
from .apiViews import (
    createPaidEvent,
    getEventFormFields,
    host_portal,
    editEvent,
    getHostStripeAccountLink,
    getTicketsForEvent,
    getCouponsForEvent
)

app_name = "eventManagementAPI"

urlpatterns = [
    path("host_portal/", host_portal, name="host_portal"),
    path("create_paid_event/", createPaidEvent, name="create_paid_event"),
    path("get_event_form_fields/", getEventFormFields, name="get_event_form_fields"),
    path("edit_event/<uuid:eventId>/", editEvent, name="edit_event"),
    path(
        "get_host_stripe_account_link/",
        getHostStripeAccountLink,
        name="get_host_stripe_account_link",
    ),
    # Event Ticketing
    path(
        "getHostEventTicketing/<uuid:eventId>/",
        getHostEventTicketing,
        name="getHostEventTicketing",
    ),
    path("getTicketsForEvent/<uuid:", getTicketsForEvent, name="getTicketsForEvent"),
    path("getCouponsForEvent/", getCouponsForEvent, name="getCouponsForEvent"),
]
