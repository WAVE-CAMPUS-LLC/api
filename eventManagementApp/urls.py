from django.urls import path
from . import views


app_name = "eventManagement"

urlpatterns = [
    path("", views.hostView, name="hostHome"),
    path("apply/", views.hostApplyView, name="hostApply"),
    path("portal/", views.hostPortalView, name="hostPortal"),
    path("guide/", views.hostGuideView, name="hostGuide"),
    path("create/", views.hostCreateEvent, name="hostCreateEvent"),
    path(
        "create/new/", views.hostCreateEventGenerator, name="hostCreateEventGenerator"
    ),
    path(
        "create/new/<uuid:eventId>/",
        views.eventCreationProcess,
        name="eventCreationProcess",
    ),
    path(
        "event/overview/<uuid:eventId>/",
        views.eventCreatedOverview,
        name="eventOverview",
    ),
    path(
        "event/<uuid:eventId>/ticketing/home/", views.eventTicketingOverview, name="ticketingOverview"
    ),
]
