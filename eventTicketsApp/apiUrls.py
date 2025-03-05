from django.urls import path
from .apiViews import (
    get_event_tickets, 
    get_ticket_details, 
    save_mobile_cart,
    get_mobile_cart,
    get_event_ticket_info
)

app_name = "eventTicketsAPI"

urlpatterns = [
    path("tickets/", get_event_tickets, name="get_event_tickets"),
    path("ticket/<str:ticketId>/", get_ticket_details, name="get_ticket_details"),
    path("mobile/cart/save/", save_mobile_cart, name="save_mobile_cart"),
    path("mobile/cart/get/", get_mobile_cart, name="get_mobile_cart"),
    # Removed ticketing prefix since it's already added in urlsapi.py
    path("event/<uuid:eventId>/tickets/", get_event_ticket_info, name="get_event_ticket_info"),
]