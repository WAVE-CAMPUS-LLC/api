from django.urls import path
from . import views


app_name = "eventManagement"

urlpatterns = [
    path("host/", views.hostView, name="hostHome"),
    path("host/portal/", views.hostPortalView, name="hostPortal"),
    path("host/guide/", views.hostGuideView, name="hostGuide"),
    # path("create/", views.hostCreateEvent, name="hostCreateEvent"),
    path("event/create/select/", views.eventCreationSelect, name="eventCreationSelect"),
    path("create/free/", views.createFreeEvent, name="createFreeEvent"),
    path("create/paid/", views.createPaidEvent, name="createPaidEvent"),
    path("tickets/<uuid:eventId>/", views.createPaidEventTicket, name="paidTicketing"),
    path("invite/<uuid:eventId>/", views.createInviteEventTicket, name="inviteTicketing"),
    path(
        "event/<uuid:eventId>/manage/",
        views.eventManagement,
        name="eventManagement",
    ),
    path(
        "event/<uuid:eventId>/edit/",
        views.editEvent,
        name="editEvent",
    ),
    path(
        "host/billing/withdraw/",
        views.hostBillingCashout,
        name="hostBillingCashout",
    ),
    path("host/analytics/", views.hostAnalyticsHome, name="hostAnalytics"),
    path(
        "analytics/event/<uuid:eventId>/",
        views.hostEventAnalytics,
        name="hostEventAnalytics",
    ),
    path("billing/add/card/new/", views.addCard, name="hostBillingAddCard"),
]
