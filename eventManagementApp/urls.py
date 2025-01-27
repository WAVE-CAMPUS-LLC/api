from django.urls import path
from . import views


app_name = "eventManagement"

urlpatterns = [
    path("", views.hostView, name="hostHome"),
    path("portal/", views.hostPortalView, name="hostPortal"),
    path("guide/", views.hostGuideView, name="hostGuide"),
    # path("create/", views.hostCreateEvent, name="hostCreateEvent"),
    
    path(
        "event/create/",
        views.eventCreationProcess,
        name="eventCreationProcess",
    ),
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
    path("analytics/event/<uuid:eventId>/", views.hostEventAnalytics, name="hostEventAnalytics"),  
    path("billing/add/card/new/", views.addCard, name="hostBillingAddCard"),
]
