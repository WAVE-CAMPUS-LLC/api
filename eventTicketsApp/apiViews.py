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
from eventManagementApp.models import Event, HostProfile, CouponCode
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
from eventManagementApp.serializers import CouponSerializer
from authenticationApp.models import CustomUser


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_event_tickets(request):
    tickets = Ticket.objects.filter(user=request.user)
    rsvp_tickets = RSVPTicket.objects.filter(email=request.user.email)
    return Response(
        {
            "tickets": TicketSerializer(tickets, many=True).data,
            "rsvpTickets": RSVPTicketSerializer(rsvp_tickets, many=True).data,
        },
        status=status.HTTP_200_OK,
    )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_event_coupons(request, eventId):
    event = get_object_or_404(Event, eventId=eventId)
    try:
        # Get all coupon codes for the event instead of using get_object_or_404
        coupons = CouponCode.objects.filter(event=event)

        if coupons.exists():
            return Response(
                {
                    "coupons": CouponSerializer(coupons, many=True).data
                }, 
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "error": "No coupons found for this event"
                }, 
                status=status.HTTP_404_NOT_FOUND,
            )
            
    except Exception as e:
        return Response(
            {
                "error": f"Error retrieving coupons: {str(e)}"
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def applyCouponCode(request, eventId, couponCode):
    """
    Apply a coupon code to the user's cart for a specific event.
    
    Parameters:
    - eventId: UUID of the event
    - couponCode: String code of the coupon to apply
    
    Returns:
    - 200 OK: Coupon applied successfully with discount information
    - 400 BAD REQUEST: Missing or invalid parameters
    - 404 NOT FOUND: Event or coupon not found
    - 500 INTERNAL SERVER ERROR: Unexpected errors
    """
    # Validate input parameters
    if not couponCode or not eventId:
        return Response(
            {
                "success": False,
                "message": "Coupon code and event ID are required"
            }, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Get event and validate it exists
        event = get_object_or_404(Event, eventId=eventId)
        
        # Get coupon and validate it exists for this event
        try:
            coupon = CouponCode.objects.get(code=couponCode, event=event)
        except CouponCode.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Invalid coupon code for this event"
                }, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get the current cart
        cart = request.session.get("cart", {})
        
        # Add the coupon code to the cart
        cart['coupon_code'] = couponCode
        
        # Save the updated cart back to the session
        request.session["cart"] = cart
        request.session.modified = True  # Ensure session is saved
        
        return Response(
            {
                "success": True,
                "message": "Coupon applied successfully",
                "discount_percentage": coupon.discount_percentage,
                "coupon_details": {
                    "code": coupon.code,
                    "discount": coupon.discount_percentage,
                }
            }, 
            status=status.HTTP_200_OK
        )
        
    except Event.DoesNotExist:
        return Response(
            {
                "success": False,
                "message": "Event not found"
            }, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:        
        return Response(
            {
                "success": False,
                "message": f"An unexpected error occurred while applying the coupon: {str(e)}"
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_mobile_cart(request):
    """Save cart data from mobile app and return web checkout URL"""
    try:
        print("Received request data:", request.data)

        # Extract and validate cart data
        cart_data = request.data.get("cart", [])
        if not isinstance(cart_data, list):
            return Response(
                {"error": "Cart data must be an array"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate required fields for each cart item
        for item in cart_data:
            missing_fields = []
            required_fields = [
                "ticket_id",
                "eventId",
                "ticket_name",
                "ticket_price",
                "quantity",
            ]

            for field in required_fields:
                if field not in item:
                    missing_fields.append(field)

            if missing_fields:
                return Response(
                    {
                        "error": "Missing required fields",
                        "missing_fields": missing_fields,
                        "received_data": item,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Format cart data for session storage
        formatted_cart = {}
        for item in cart_data:
            ticket_id = item["ticket_id"]
            formatted_cart[ticket_id] = {
                "eventId": item["eventId"],
                "name": item["ticket_name"],
                "price": str(item["ticket_price"]),
                "quantity": item["quantity"],
            }

        # Generate a unique cart ID
        cart_id = str(uuid.uuid4())

        # Store cart in session with the unique ID
        request.session[f"mobile_cart_{cart_id}"] = formatted_cart
        print("Stored cart data:", formatted_cart)

        # Build the web checkout URL with cart ID
        web_base_url = settings.SITE_URL
        checkout_path = reverse("eventTicketsAPI:processCheckout")
        params = urlencode({"cart_id": cart_id})
        web_checkout_url = f"{web_base_url}{checkout_path}?{params}"

        return Response(
            {
                "message": "Cart saved successfully",
                "cartSaved": True,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        print(f"Error saving mobile cart: {str(e)}")
        return Response(
            {"error": str(e), "received_data": request.data},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_mobile_cart(request):
    """Retrieve saved cart data by cart ID"""
    try:
        cart_id = request.GET.get("cart_id")
        if not cart_id:
            return Response(
                {"error": "cart_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        cart = request.session.get(f"mobile_cart_{cart_id}", {})
        return Response({"cart": cart}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_ticket_info(request, ticketId):
    """Get ticket info for mobile app with proper UUID handling"""
    try:
        # Ensure ticketId is treated as UUID
        ticket_uuid = uuid.UUID(str(ticketId))
        ticket = get_object_or_404(Ticket, ticketId=ticket_uuid)
        return Response(TicketSerializer(ticket).data, status=status.HTTP_200_OK)
    except ValueError:
        return Response(
            {"error": f"Invalid ticket ID format: {ticketId}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response(
            {"error": f"Error retrieving ticket: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


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
            ticket_info.append(
                {
                    "id": str(ticket.ticket_id),
                    "name": ticket.ticket_name,
                    "price": str(ticket.ticket_price),
                    "description": ticket.ticket_description,
                    "quantity_available": ticket.available_tickets(),
                    "stripe_price_id": ticket.stripePriceId,
                    "event_id": str(event.eventId),  # Add event_id to response
                }
            )

        return Response(
            {"event_id": str(event.eventId), "tickets": ticket_info},
            status=status.HTTP_200_OK,
        )
    except Event.DoesNotExist:
        return Response(
            {"error": f"Event with ID {eventId} not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def processCheckout(request):
    cart = request.data.get("cart", {})
    print("Received cart data in process checkout: ", cart)
    if not cart:
        return Response({"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)

    # Check if there's a valid coupon code in the cart
    has_discount = False
    discount_percentage = 0
    
    # Get the discount percentage directly from the cart if it exists
    if 'discount_percentage' in cart:
        discount_percentage = float(cart.get('discount_percentage'))
        has_discount = True
        print(f"Using discount percentage from cart: {discount_percentage}%")
    elif 'coupon_code' in cart:
        coupon_code_value = cart.get('coupon_code')
        # We'll validate the coupon later, just note that there might be a discount
    
    # Filter out any non-ticket items (like coupon_code) for total calculation
    ticket_items = {}
    for k, v in cart.items():
        if k == 'coupon_code' or k == 'discount_percentage':
            continue
        if isinstance(v, dict) and "price" in v and "quantity" in v:
            ticket_items[k] = v
        else:
            print(f"Skipping non-ticket item: {k} = {v}")
    
    print(f"Ticket items: {ticket_items}")
    
    if not ticket_items:
        return Response({"error": "No valid tickets in cart"}, status=status.HTTP_400_BAD_REQUEST)

    # Calculate the total amount for tickets
    total_amount = sum(
        float(item.get("price", 0)) * int(item.get("quantity", 0))
        for item in ticket_items.values()
    )
    amount_in_cents = int(total_amount * 100)
    
    # Only reject zero-amount carts if there's no discount applied
    # If there's a 100% discount, we should allow the checkout to proceed
    if amount_in_cents <= 0 and not has_discount and discount_percentage < 100:
        return Response({"error": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

    # Get platform settings for fees
    platform_settings = StripePlatformSettings.objects.first()
    if not platform_settings:
        platform_settings = StripePlatformSettings.objects.create()

    # Get event and host info
    first_ticket_key = next(iter(ticket_items.keys()))
    first_ticket = ticket_items[first_ticket_key]
    event_id = first_ticket.get("eventId")
    
    try:
        event = Event.objects.get(eventId=event_id)
        host = CustomUser.objects.get(id=event.host.id)
        
        # Check if there's a valid coupon code in the cart
        valid_coupon_code = False
        
        # Initialize coupon_code_value to None before checking
        coupon_code_value = None
        
        # Get the coupon code from the cart if it exists
        if 'coupon_code' in cart:
            coupon_code_value = cart.get('coupon_code')
        
        # Get the discount percentage directly from the cart if it exists
        if 'discount_percentage' in cart:
            discount_percentage = float(cart.get('discount_percentage'))
            valid_coupon_code = True
            print(f"Using discount percentage from cart: {discount_percentage}%")
        elif coupon_code_value:
            try:
                # Try to get the coupon code object for this event
                from eventManagementApp.models import CouponCode
                coupon = CouponCode.objects.get(code=coupon_code_value, event=event)
                
                # Coupons no longer expire - all coupons are valid
                valid_coupon_code = True
                discount_percentage = coupon.discount_percentage
                print(f"Valid coupon applied: {coupon_code_value}, Discount: {discount_percentage}%")
            except CouponCode.DoesNotExist:
                # Coupon doesn't exist or doesn't belong to this event
                valid_coupon_code = False
                print(f"Coupon not found: {coupon_code_value}")
        
        # Calculate original amount for service fee calculation
        original_amount = sum(
            float(item.get("originalPrice", item.get("price", 0))) * int(item.get("quantity", 0))
            for item in ticket_items.values()
        )
        original_amount_in_cents = int(original_amount * 100)
        
        # Calculate service fee based on platform settings
        percentage_fee = (total_amount * float(platform_settings.salesTaxPercentage)) / 100
        fixed_fee = float(platform_settings.salesFeeAmount)
        
        if amount_in_cents <= 0 and has_discount and discount_percentage >= 100:
            # For 100% discounts, apply a minimal service fee based on the original price
            fee_amount = max(99, int(original_amount_in_cents * 0.07) + 99)
        else:
            fee_amount = int((percentage_fee + fixed_fee) * 100)  # Convert to cents

        # Build Stripe line items
        line_items = []
        for key, ticket in ticket_items.items():
            unit_amount = int(Decimal(ticket["price"]) * 100)
            print(f"Using price for {ticket['name']}: {ticket['price']}, Unit amount: {unit_amount}")
            
            # For 100% discounts, we still want to show the ticket in the checkout
            # but with a zero price
            if unit_amount == 0 and has_discount and discount_percentage >= 100:
                # Add a note to the ticket name to indicate it's free due to a coupon
                ticket_name = f"{ticket['name']} (100% discount applied)"
                # Store the original ticket info in metadata
                metadata = {
                    'original_ticket_name': ticket['name'],
                    'original_ticket_id': key,
                    'event_id': ticket.get('eventId'),
                    'is_discounted': 'true',
                    'discount_percentage': str(discount_percentage)
                }
            else:
                ticket_name = ticket["name"]
                metadata = {
                    'original_ticket_name': ticket['name'],
                    'original_ticket_id': key,
                    'event_id': ticket.get('eventId')
                }
                
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": ticket_name,
                        "metadata": metadata
                    },
                    "unit_amount": unit_amount,
                },
                "quantity": ticket["quantity"],
            })

        # For 100% discounts, we need to ensure there's at least one non-zero item
        # (the service fee) to make Stripe checkout work
        if not (amount_in_cents <= 0 and has_discount and discount_percentage >= 100):
            # Regular service fee for non-100% discounted tickets
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Service Fee",
                    },
                    "unit_amount": fee_amount,
                },
                "quantity": 1,
            })

        try:
            print(f"Creating Stripe checkout session with {len(line_items)} line items")
            
            # For 100% discounts, we need to handle the payment intent differently
            # since there's no ticket amount to transfer to the host
            if amount_in_cents <= 0 and has_discount and discount_percentage >= 100:
                # For 100% discounted tickets, the service fee is the entire amount
                # and there's no transfer to the host's account
                checkout_session = stripe.checkout.Session.create(
                    customer=request.user.customer_id if request.user.is_authenticated else None,
                    payment_method_types=["card"],
                    line_items=line_items,
                    mode="payment",
                    # No payment_intent_data with transfer since the entire amount is the service fee
                    success_url=request.build_absolute_uri(
                        (reverse("eventTickets:paymentSuccessful"))
                        + "?session_id={CHECKOUT_SESSION_ID}"
                        + "&from_mobile=true"
                    ),
                    cancel_url=request.build_absolute_uri(
                        (reverse("eventTickets:paymentFailed")) + "?from_mobile=true"
                    ),
                    metadata={
                        'cart_data': json.dumps(cart),  # Store the entire cart in metadata
                        'event_id': str(event.eventId),
                        'event_title': event.title,
                        'is_discounted': 'true',
                        'discount_percentage': str(discount_percentage)
                    }
                )
            else:
                # Regular checkout with transfer to host's account
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
                        # Add metadata to help with cart reconstruction
                        "metadata": {
                            'cart_data': json.dumps(cart),  # Store the entire cart in metadata
                            'event_id': str(event.eventId),
                            'event_title': event.title,
                            'discount_percentage': str(discount_percentage) if has_discount else '0'
                        }
                    },
                    metadata={
                        'cart_data': json.dumps(cart),  # Store the entire cart in metadata
                        'event_id': str(event.eventId),
                        'event_title': event.title,
                        'discount_percentage': str(discount_percentage) if has_discount else '0'
                    },
                    success_url=request.build_absolute_uri(
                        (reverse("eventTickets:paymentSuccessful"))
                        + "?session_id={CHECKOUT_SESSION_ID}"
                        + "&from_mobile=true"
                    ),
                    cancel_url=request.build_absolute_uri(
                        (reverse("eventTickets:paymentFailed")) + "?from_mobile=true"
                    ),
                )
            
            print(f"Checkout session created: {checkout_session.id}")
            return Response({"sessionUrl": checkout_session.url}, status=status.HTTP_200_OK)
        
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e}")
            return Response({"error": f"Stripe error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
    except Event.DoesNotExist:
        return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)
    except CustomUser.DoesNotExist:
        return Response({"error": "Host not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        import traceback
        print(f"Unexpected error in processCheckout: {e}")
        print(traceback.format_exc())
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def mobile_payment_success(request):
    """Handle successful mobile payment and generate tickets"""
    session_id = request.data.get("session_id")
    if not session_id:
        return Response(
            {"error": "Session ID is required"}, status=status.HTTP_400_BAD_REQUEST
        )

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

        return Response(
            {"message": "Payment successful and tickets generated"},
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_ticket(request):
    try:
        # Get ticket ID from request body
        ticket_id = request.data.get('ticketId')
        
        if not ticket_id:
            return Response({
                'valid': False,
                'message': 'Ticket ID is required',
                'received': request.data
            }, status=status.HTTP_400_BAD_REQUEST)

        # Log the received data for debugging
        print(f"Verifying ticket: {ticket_id}")
        print(f"Request data: {request.data}")

        try:
            ticket = Ticket.objects.get(ticketId=ticket_id)
        except Ticket.DoesNotExist:
            return Response({
                'valid': False,
                'message': 'Ticket not found',
                'ticketData': {
                    'status': 'Invalid'
                }
            }, status=status.HTTP_404_NOT_FOUND)

        # Update ticket status if provided
        new_status = request.data.get('status')
        if new_status:
            ticket.status = new_status
            ticket.save()

        # Return ticket data
        return Response({
            'valid': True,
            'message': 'Ticket status updated successfully',
            'ticketData': get_ticket_data(ticket)
        }, status=status.HTTP_200_OK)

    except Exception as e:
        error_msg = f"Verification error: {str(e)}"
        print(error_msg)
        return Response({
            'valid': False,
            'message': 'Error processing ticket',
            'error': str(e),
            'received_data': request.data
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_ticket_data(ticket):
    return {
        "guestFirstName": (
            ticket.guestFirstName if ticket.guestFirstName else ticket.user.first_name
        ),
        "guestLastName": (
            ticket.guestLastName if ticket.guestLastName else ticket.user.last_name
        ),
        "userFirstName": ticket.user.first_name if ticket.user else None,
        "userLastName": ticket.user.last_name if ticket.user else None,
        "status": ticket.status,
    }
