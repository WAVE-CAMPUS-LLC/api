from django.urls import path
from . import views


app_name = "eventManagement"

urlpatterns = [
    path("", views.hostView, name="hostHome"),
    path("portal/", views.hostPortalView, name="hostPortal"),
    path("guide/", views.hostGuideView, name="hostGuide"),
    # path("create/", views.hostCreateEvent, name="hostCreateEvent"),
    path("event/create/select/", views.eventCreationSelect, name="eventCreationSelect"),
    path(
        "create/rsvp/",
        views.createRsvpEvent,
        name="createRsvpEvent",
    ),
    path("create/invite", views.createInviteEvent, name="createInviteEvent"),
    path("create/paid", views.createPaidEvent, name="createPaidEvent"),
    path(
        "event/<uuid:eventId>/manage/",
        views.eventManagement,
        name="eventManagement",
    ),
    path(
        "billing/withdraw/",
        views.hostBillingCashout,
        name="hostBillingCashout",
    ),
    path("analytics/", views.hostAnalyticsHome, name="hostAnalytics"),
    path(
        "analytics/event/<uuid:eventId>/",
        views.hostEventAnalytics,
        name="hostEventAnalytics",
    ),
    path("billing/add/card/new/", views.addCard, name="hostBillingAddCard"),
]
