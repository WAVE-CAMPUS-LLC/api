from django.urls import path
from .apiViews import (
    get_event_tickets, 
    save_mobile_cart,
    get_mobile_cart,
    get_event_ticket_info,
    processCheckout,
    get_user_ticket_info
)

app_name = "eventTicketsAPI"

urlpatterns = [
    path("tickets/", get_event_tickets, name="get_event_tickets"),
    path("mobile/cart/save/", save_mobile_cart, name="save_mobile_cart"),
    path("mobile/cart/get/", get_mobile_cart, name="get_mobile_cart"),
    # Removed ticketing prefix since it's already added in urlsapi.py
    path("event/<uuid:eventId>/tickets/", get_event_ticket_info, name="get_event_ticket_info"),
    path("ticketing/get_user_ticket_info/<str:ticketId>/", get_user_ticket_info, name="get_user_ticket_info"),
    path('checkout/', processCheckout, name="processCheckout"),
]