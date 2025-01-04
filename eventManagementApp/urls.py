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
        "event/save-progress/<uuid:eventId>/",
        views.save_event_progress,
        name="save_event_progress",
    ),
    path(
        "event/<uuid:eventId>/manage/",
        views.eventManagement,
        name="eventManagement",
    ),
    path(
        "billing/",
        views.hostBilling,
        name="hostBilling",
    ),
    path(
        "billing/withdraw/",
        views.hostBillingCashout,
        name="hostBillingCashout",
    ),
    path("analytics/", views.hostAnalyticsHome, name="hostAnalytics"),
    path("analytics/event/<uuid:eventId>/", views.hostEventAnalytics, name="hostEventAnalytics"),  
    path("billing/add/card/new/", views.addCard, name="hostBillingAddCard"),
]
