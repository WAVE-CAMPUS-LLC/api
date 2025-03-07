from datetime import datetime
import time
import json
import stripe
from django import forms
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from eventManagementApp.models import Event, HostProfile
from .serializers import EventSerializer
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
from django.urls import reverse
import uuid
from urllib.parse import urlencode

from wave_v1.decorators import host, check_suspension
from accountManagementApp.models import UserProfile
from collegeManagementApp.models import Organization, OrganizationMembership
from .models import Ticket, RSVPTicket, PaidFreeTicket, StripePlatformSettings
from .serializers import TicketSerializer, RSVPTicketSerializer
from authenticationApp.models import CustomUser


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_event_tickets(request):
    tickets = Ticket.objects.filter(user=request.user)
    rsvp_tickets = RSVPTicket.objects.filter(email=request.user.email)
    return Response(
        {
            "tickets": TicketSerializer(tickets, many=True).data,
            "rsvpTickets": RSVPTicketSerializer(rsvp_tickets, many=True).data, },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_mobile_cart(request):
    """Save cart data from mobile app and return web checkout URL"""
    try:
        print("Received request data:", request.data)
        
        # Extract and validate cart data
        cart_data = request.data.get('cart', [])
        if not isinstance(cart_data, list):
            return Response(
                {"error": "Cart data must be an array"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate required fields for each cart item
        for item in cart_data:
            missing_fields = []
            required_fields = ['ticket_id', 'eventId', 'ticket_name', 'ticket_price', 'quantity']
            
            for field in required_fields:
                if field not in item:
                    missing_fields.append(field)
            
            if missing_fields:
                return Response(
                    {
                        "error": "Missing required fields", 
                        "missing_fields": missing_fields,
                        "received_data": item
                    }, 
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Format cart data for session storage
        formatted_cart = {}
        for item in cart_data:
            ticket_id = item['ticket_id']
            formatted_cart[ticket_id] = {
                'eventId': item['eventId'],
                'name': item['ticket_name'],
                'price': str(item['ticket_price']),
                'quantity': item['quantity']
            }
        
        # Generate a unique cart ID
        cart_id = str(uuid.uuid4())
        
        # Store cart in session with the unique ID
        request.session[f'mobile_cart_{cart_id}'] = formatted_cart
        print("Stored cart data:", formatted_cart)
        
        # Build the web checkout URL with cart ID
        web_base_url = settings.SITE_URL
        checkout_path = reverse('eventTicketsAPI:processCheckout')
        params = urlencode({'cart_id': cart_id})
        web_checkout_url = f"{web_base_url}{checkout_path}?{params}"
        
        return Response({
            "message": "Cart saved successfully",
            "cartSaved": True,
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error saving mobile cart: {str(e)}")
        return Response(
            {
                "error": str(e),
                "received_data": request.data
            }, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_mobile_cart(request):
    """Retrieve saved cart data by cart ID"""
    try:
        cart_id = request.GET.get('cart_id')
        if not cart_id:
            return Response({"error": "cart_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        cart = request.session.get(f'mobile_cart_{cart_id}', {})
        return Response({"cart": cart}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_event_ticket_info(request, eventId):
    """Get available tickets for an event"""
    try:
        # Try both path formats - with or without ticketing prefix
        event = get_object_or_404(Event, eventId=eventId)
        tickets = PaidFreeTicket.objects.filter(event=event)

        ticket_info = []
        for ticket in tickets:
            ticket_info.append({
                'id': str(ticket.ticket_id),
                'name': ticket.ticket_name,
                'price': str(ticket.ticket_price),
                'description': ticket.ticket_description,
                'quantity_available': ticket.available_tickets(),
                'stripe_price_id': ticket.stripePriceId,
                'event_id': str(event.eventId)  # Add event_id to response
            })

        return Response({
            'event_id': str(event.eventId),
            'tickets': ticket_info
        }, status=status.HTTP_200_OK)
    except Event.DoesNotExist:
        return Response(
            {"error": f"Event with ID {eventId} not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def processCheckout(request):
    cart = request.data.get("cart", {})
    print("Received cart data in process checkout: ", cart)
    if not cart:
        return Response({"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Calculate the total amount for tickets
    total_amount = sum(
        float(item.get("price", 0)) * int(item.get("quantity", 0))
        for item in cart.values()
    )
    amount_in_cents = int(total_amount * 100)
    if amount_in_cents <= 0:
        return Response({"error": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

    # Get platform settings for fees
    platform_settings = StripePlatformSettings.objects.first()
    if not platform_settings:
        platform_settings = StripePlatformSettings.objects.create()
    
    # Calculate service fee based on platform settings
    percentage_fee = (total_amount * float(platform_settings.salesTaxPercentage)) / 100
    fixed_fee = float(platform_settings.salesFeeAmount)
    fee_amount = int((percentage_fee + fixed_fee) * 100)  # Convert to cents

    # Build Stripe line items
    line_items = []
    for ticket in cart.values():
        line_items.append({
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": ticket["name"],
                },
                "unit_amount": int(Decimal(ticket["price"]) * 100),
            },
            "quantity": ticket["quantity"],
        })
    
    # Add service fee as separate line item
    # line_items.append({
    #     "price_data": {
    #         "currency": "usd",
    #         "product_data": {
    #             "name": "Service Fee",
    #         },
    #         "unit_amount": fee_amount,
    #     },
    #     "quantity": 1,
    # })

    # Get event and host info
    first_ticket = next(iter(cart.values()))
    event = Event.objects.get(eventId=first_ticket.get("eventId"))
    host = CustomUser.objects.get(id=event.host.id)

    try:
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=request.user.customer_id if request.user.is_authenticated else None,
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            payment_intent_data={
                "application_fee_amount": fee_amount,
                "transfer_data": {
                    "destination": host.connectAccountID,
                },
            },
            success_url="myapp://paymentSuccessful?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="myapp://paymentFailed",
        )
        

        return Response({
            "sessionUrl": checkout_session.url
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
@permission_classes([AllowAny])
def mobile_payment_success(request):
    """Handle successful mobile payment and generate tickets"""
    session_id = request.data.get("session_id")
    if not session_id:
        return Response({"error": "Session ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        cart = request.session.get("cart", {})

        for cart_key, ticket_info in cart.items():
            event_id = ticket_info.get("eventId")
            if not event_id:
                continue

            try:
                event = Event.objects.get(eventId=event_id)
            except Event.DoesNotExist:
                continue

            if "_crew_" in cart_key or "crewId" in ticket_info:
                crew_id = ticket_info["crewId"]
                try:
                    from socialApp.models import Crew
                    crew = Crew.objects.get(crewId=crew_id)
                    for member in crew.members.all():
                        Ticket.objects.create(
                            user=member if member else None,
                            event=event,
                            guestFirstName=member.first_name if member else None,
                            guestLastName=member.last_name if member else None,
                            guestEmail=member.email if member else None,
                        )
                except Crew.DoesNotExist:
                    continue
            else:
                if request.user.is_authenticated:
                    first_name = request.user.first_name
                    last_name = request.user.last_name
                    email = request.user.email
                else:
                    name_parts = session.customer_details.name.split()
                    first_name = name_parts[0] if name_parts else ""
                    last_name = name_parts[-1] if len(name_parts) > 1 else ""
                    email = session.customer_details.email

                quantity = ticket_info.get("quantity", 1)
                for _ in range(quantity):
                    Ticket.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        event=event,
                        guestFirstName=first_name,
                        guestLastName=last_name,
                        guestEmail=email,
                    )

        # Clean up session data
        if "cart" in request.session:
            del request.session["cart"]

        return Response({"message": "Payment successful and tickets generated"}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)