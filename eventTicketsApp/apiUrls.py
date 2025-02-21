from django.urls import path
from .apiViews import get_event_tickets, get_ticket_details


app_name = "eventTicketsAPI"

urlpatterns = [
    path("/tickets/", get_event_tickets, name="get_event_tickets"),
    path("/ticket/<str:ticketId>/", get_ticket_details, name="get_ticket_details"),
]