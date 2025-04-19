from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from asgiref.sync import sync_to_async
import uuid
import json
import stripe
import asyncio
from decimal import Decimal
from urllib.parse import urlencode
from functools import partial
import os

from django.conf import settings
from django.urls import reverse
from eventTicketsApp.models import Ticket, RSVPTicket, StripePlatformSettings, PaidFreeTicket
from eventManagementApp.models import Event, CouponCode
from authenticationApp.models import CustomUser
from fastapi import Depends
from apiManager.dependencies import get_current_user
from eventTicketsApp.serializers import TicketSerializer


router = APIRouter()


# Helper functions for async Django ORM operations
async def get_event(event_id):
    """Get an event by ID asynchronously"""
    return await sync_to_async(Event.objects.get)(eventId=event_id)

async def get_host_id(event):
    """Get the host ID from an event asynchronously"""
    # We need to use a lambda to access the related field in a sync context
    return await sync_to_async(lambda: event.host.id)()

async def get_host(host_id):
    """Get a host by ID asynchronously"""
    return await sync_to_async(CustomUser.objects.get)(id=host_id)

async def get_platform_settings():
    """Get platform settings asynchronously"""
    settings = await sync_to_async(StripePlatformSettings.objects.first)()
    if not settings:
        settings = await sync_to_async(StripePlatformSettings.objects.create)()
    return settings

async def get_coupon(code, event):
    """Get a coupon by code and event asynchronously"""
    try:
        return await sync_to_async(CouponCode.objects.get)(code=code, event=event)
    except CouponCode.DoesNotExist:
        return None

async def get_user(user_id):
    """Get a user by ID asynchronously"""
    try:
        return await sync_to_async(CustomUser.objects.get)(id=user_id)
    except CustomUser.DoesNotExist:
        return None


class TicketItem(BaseModel):
    """Pydantic model for a ticket item in the cart"""
    name: str
    price: str
    quantity: int
    eventId: str
    crewId: Optional[str] = None


class CartData(BaseModel):
    """Pydantic model for the cart data"""
    cart: Dict[str, Union[Dict[str, Any], str, float]]
    

class CheckoutResponse(BaseModel):
    """Pydantic model for the checkout response"""
    sessionUrl: str


@router.post("/processCheckout", response_model=CheckoutResponse, status_code=status.HTTP_200_OK)
async def process_checkout(
    request: Request, 
    cart_data: CartData = Body(...),
    user_id: Optional[str] = Depends(get_current_user)
):
    print(f"[process_checkout] Function called with user_id: {user_id}")
    """Process checkout for event tickets using Stripe
    
    This endpoint handles the creation of a Stripe checkout session for purchasing event tickets.
    It supports coupon codes, discounts, and handles special cases like 100% discounts.
    
    Args:
        request: The FastAPI request object
        cart_data: The cart data containing tickets and optional coupon information
        user_id: The authenticated user ID (optional)
        
    Returns:
        A JSON response with the Stripe checkout session URL
    """
    # Extract cart from the request body
    cart = cart_data.cart
    print("Received cart data in process checkout: ", cart)
    
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty"
        )
    
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid tickets in cart"
        )

    # Calculate the total amount for tickets (without discount)
    total_amount = sum(
        float(item.get("price", 0)) * int(item.get("quantity", 0))
        for item in ticket_items.values()
    )
    
    # Get platform settings for fees using our helper function
    platform_settings = await get_platform_settings()

    # Get event and host info
    first_ticket_key = next(iter(ticket_items.keys()))
    first_ticket = ticket_items[first_ticket_key]
    event_id = first_ticket.get("eventId")
    
    try:
        # Get event and host using our helper functions
        event = await get_event(event_id)
        host_id = await get_host_id(event)
        host = await get_host(host_id)
        
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
            # Try to get the coupon code object for this event using our helper function
            coupon = await get_coupon(coupon_code_value, event)
            
            if coupon:
                # Coupons no longer expire - all coupons are valid
                valid_coupon_code = True
                # We need to access the discount_percentage in a sync context
                discount_percentage = await sync_to_async(lambda: coupon.discount_percentage)()
                print(f"Valid coupon applied: {coupon_code_value}, Discount: {discount_percentage}%")
            else:
                # Coupon doesn't exist or doesn't belong to this event
                valid_coupon_code = False
                print(f"Coupon not found: {coupon_code_value}")
        
        # Store original amount for reference
        original_amount = total_amount
        original_amount_in_cents = int(original_amount * 100)
        
        # Apply discount to the total amount if a valid coupon is present
        if valid_coupon_code and discount_percentage > 0:
            discount_amount = total_amount * (discount_percentage / 100)
            total_amount = total_amount - discount_amount
            has_discount = True
            print(f"Applied {discount_percentage}% discount: Original: ${original_amount}, Discount: ${discount_amount}, New total: ${total_amount}")
        
        # Convert to cents after discount is applied
        amount_in_cents = int(total_amount * 100)
        
        # Only reject zero-amount carts if there's no discount applied
        # If there's a 100% discount, we should allow the checkout to proceed
        if amount_in_cents <= 0 and not has_discount and discount_percentage < 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid amount"
            )
        
        # Calculate service fee: 7% of subtotal + $0.99 flat fee
        # This matches the calculation in the Django hostedCheckout implementation
        
        if amount_in_cents <= 0 and has_discount and discount_percentage >= 100:
            # For 100% discounts, apply a minimal service fee based on the original price
            fee_amount = max(99, int(original_amount_in_cents * 0.07) + 99)
        else:
            fee_amount = int(amount_in_cents * 0.07) + 99  # 7% of subtotal + $0.99 flat fee in cents
        
        print(f"Service fee: ${fee_amount/100} calculated on discounted amount: ${total_amount}")

        # Build Stripe line items
        line_items = []
        for key, ticket in ticket_items.items():
            # Calculate the discounted price for each ticket
            original_price = float(ticket["price"])
            
            if valid_coupon_code and discount_percentage > 0:
                discounted_price = original_price * (1 - discount_percentage / 100)
                unit_amount = int(Decimal(discounted_price) * 100)
                print(f"Discounted price for {ticket['name']}: Original: ${original_price}, Discounted: ${discounted_price}, Unit amount: {unit_amount}")
            else:
                unit_amount = int(Decimal(original_price) * 100)
                print(f"Using original price for {ticket['name']}: ${original_price}, Unit amount: {unit_amount}")
            
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
                    'discount_percentage': str(discount_percentage),
                    'original_price': str(original_price)
                }
            else:
                ticket_name = ticket["name"]
                if valid_coupon_code and discount_percentage > 0:
                    ticket_name = f"{ticket['name']} ({discount_percentage}% discount applied)"
                
                metadata = {
                    'original_ticket_name': ticket['name'],
                    'original_ticket_id': key,
                    'event_id': ticket.get('eventId'),
                    'original_price': str(original_price)
                }
                
                if valid_coupon_code and discount_percentage > 0:
                    metadata['is_discounted'] = 'true'
                    metadata['discount_percentage'] = str(discount_percentage)
                
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
            
            # Get the current user if authenticated using our helper function
            current_user = None
            if user_id:
                current_user = await get_user(user_id)
            
            # Get event information needed for both checkout paths
            event_title = await sync_to_async(lambda: event.title)()  
            event_id_str = await sync_to_async(lambda: str(event.eventId))()  
            
            # For 100% discounts, we need to handle the payment intent differently
            # since there's no ticket amount to transfer to the host
            if amount_in_cents <= 0 and has_discount and discount_percentage >= 100:
                # For 100% discounted tickets, the service fee is the entire amount
                # and there's no transfer to the host's account
                
                # Get the success and cancel URLs
                success_url = await sync_to_async(lambda: os.getenv("WEBSITE_DOMAIN") + reverse('eventTickets:paymentSuccessful'))()
                cancel_url = await sync_to_async(lambda: os.getenv("WEBSITE_DOMAIN") + reverse('eventTickets:paymentFailed'))()
                
                checkout_session = stripe.checkout.Session.create(
                    customer=current_user.customer_id if current_user else None,
                    payment_method_types=["card"],
                    line_items=line_items,
                    mode="payment",
                    # No payment_intent_data with transfer since the entire amount is the service fee
                    success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}&from_mobile=true",
                    cancel_url=f"{cancel_url}?from_mobile=true",
                    metadata={
                        'cart_data': json.dumps(cart),  # Store the entire cart in metadata
                        'event_id': event_id_str,  # Using the already async-safe event ID
                        'event_title': event_title,  # Using the already async-safe event title
                        'is_discounted': 'true',
                        'discount_percentage': str(discount_percentage),
                        'original_amount': str(original_amount),
                        'discounted_amount': str(total_amount)
                    }
                    
                )
            else:
                # Regular checkout with transfer to host's account
                
                # Get the success and cancel URLs if not already defined
                if not locals().get('success_url'):
                    success_url = await sync_to_async(lambda: os.getenv("WEBSITE_DOMAIN") + reverse('eventTickets:paymentSuccessful'))()
                    cancel_url = await sync_to_async(lambda: os.getenv("WEBSITE_DOMAIN") + reverse('eventTickets:paymentFailed'))()
                
                # Get the host's connect account ID in a sync context
                connect_account_id = await sync_to_async(lambda: host.connectAccountID)()
                
                checkout_session = stripe.checkout.Session.create(
                    customer=current_user.customer_id if current_user else None,
                    payment_method_types=["card"],
                    line_items=line_items,
                    mode="payment",
                    payment_intent_data={
                        # This tells Stripe to transfer only the ticket amount to the host
                        # The service fee stays with the platform
                        "transfer_data": {
                            "destination": connect_account_id,
                            "amount": amount_in_cents,  # Only transfer the ticket amount, not the fee
                        },
                        # Add metadata to help with cart reconstruction
                        "metadata": {
                            'cart_data': json.dumps(cart),  # Store the entire cart in metadata
                            'event_id': event_id_str,
                            'event_title': event_title,
                            'discount_percentage': str(discount_percentage) if has_discount else '0',
                            'ticket_amount': str(amount_in_cents),
                            'fee_amount': str(fee_amount)
                        }
                    },
                    metadata={
                        'cart_data': json.dumps(cart),  # Store the entire cart in metadata
                        'event_id': event_id_str,
                        'event_title': event_title,
                        'discount_percentage': str(discount_percentage) if has_discount else '0',
                        'original_amount': str(original_amount),
                        'discounted_amount': str(total_amount)
                    },
                    success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
                    cancel_url=f"{cancel_url}?from_mobile=true",
                )
            
            print(f"Checkout session created: {checkout_session.id}")
            print(f"[process_checkout] Created checkout session with ID: {checkout_session.id}")
            print(f"[process_checkout] Returning checkout URL for user: {user_id}")
            print(f"[process_checkout] Checkout URL: {success_url}?session_id={{CHECKOUT_SESSION_ID}}")
            return {"sessionUrl": checkout_session.url}
        
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stripe error: {str(e)}"
            )
        
    except Event.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    except CustomUser.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host not found"
        )
    except Exception as e:
        import traceback
        print(f"Unexpected error in process_checkout: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
@router.get("/ticketDetails")
async def ticket_details(request: Request):
    print(f"[ticket_details] Function called with ticket ID: {request.query_params.get('ticketId')}")
    
    @sync_to_async
    def get_ticket_details(ticket_id):
        try:
            ticket = Ticket.objects.get(ticketId=ticket_id)
            event = ticket.event

            return {
                "ticketId": ticket.ticketId,
                "event": {
                    "eventId": event.eventId,
                    "eventTitle": event.title,
                    "eventLocation": {
                        "street": event.street,
                        "city": event.city,
                        "state": event.state,
                        "zip_code": event.zip_code,
                        "building_name": event.building_name
                    }
                },
                "status": ticket.status,
                "firstName": ticket.user.first_name if ticket.user else ticket.guestFirstName,
                "lastName": ticket.user.last_name if ticket.user else ticket.guestLastName,
            }
        except Ticket.DoesNotExist:
            return None
        except Exception as e:
            return {"error": str(e)}
    
    ticket_id = request.query_params.get("ticketId")
    result = await get_ticket_details(ticket_id)
    if result is None:
        print(f"[ticket_details] Ticket not found: {ticket_id}")
        return {"error": "Ticket not found"}
    print(f"[ticket_details] Successfully retrieved ticket details for: {ticket_id}")
    return result


@router.post("/activateTicket")
async def activate_ticket(request: Request):
    print(f"[activate_ticket] Function called with ticket ID: {request.query_params.get('ticketId')}")
    @sync_to_async
    def activate_user_ticket(ticket_id):
        try:
            ticket = Ticket.objects.get(ticketId=ticket_id)
            event = ticket.event
            if ticket.status == "Scanned":
                return {
                        "valid": False,
                        "message": "Ticket is already activated.",
                        "ticketData": {
                            "guestFirstName": (
                                ticket.guestFirstName
                                if ticket.guestFirstName
                                else ticket.user.first_name
                            ),
                            "guestLastName": (
                                ticket.guestLastName
                                if ticket.guestLastName
                                else ticket.user.last_name
                            ),
                            "userFirstName": (
                                ticket.user.first_name if ticket.user else None
                            ),
                            "userLastName": (
                                ticket.user.last_name if ticket.user else None
                            ),
                            "status": (ticket.status),
                        },
                    }
            elif ticket.status == "Invalid":
                return {
                        "valid": False,
                        "message": "Ticket is invalid.",
                        "ticketData": {
                            "guestFirstName": (
                                ticket.guestFirstName
                                if ticket.guestFirstName
                                else ticket.user.first_name
                            ),
                            "guestLastName": (
                                ticket.guestLastName
                                if ticket.guestLastName
                                else ticket.user.last_name
                            ),
                            "userFirstName": (
                                ticket.user.first_name if ticket.user else None
                            ),
                            "userLastName": (
                                ticket.user.last_name if ticket.user else None
                            ),
                            "status": (ticket.status),
                        },
                    }
            ticket.status = "Scanned"
            ticket.save()
            return {"valid": True, "message": "Ticket is activated", "ticketData": {
                "ticketId": ticket.ticketId,
                "event": {
                    "eventId": event.eventId,
                    "eventTitle": event.title,
                    "eventLocation": {
                        "street": event.street,
                        "city": event.city,
                        "state": event.state,
                        "zip_code": event.zip_code,
                        "building_name": event.building_name
                    }
                },
                "status": ticket.status
            }}
        except Ticket.DoesNotExist:
            return {"valid": False, "message": "Ticket not found"}
        except Exception as e:
            return {"valid": False, "message": f"An error occurred: {e}"}
        
    ticket_id = request.query_params.get("ticketId")
    result = await activate_user_ticket(ticket_id)
    print(f"[activate_ticket] Result for ticket {ticket_id}: {result.get('message', 'No message')}")
    return result


# Pydantic models for the new endpoints
class TicketTypeResponse(BaseModel):
    """Pydantic model for ticket type response"""
    ticket_id: str
    ticket_name: str
    ticket_price: float
    ticket_description: str
    ticket_quantity: int
    ticket_sold: int
    available_tickets: int
    crew_discounted_price: Optional[float] = None


class TicketTypesResponse(BaseModel):
    """Pydantic model for ticket types response"""
    event_id: str
    event_title: str
    ticket_types: List[TicketTypeResponse]


class AttendeeResponse(BaseModel):
    """Pydantic model for attendee response"""
    ticket_id: str
    first_name: str
    last_name: str
    email: str
    ticket_type: str
    purchase_date: str
    status: str


class AttendeesResponse(BaseModel):
    """Pydantic model for attendees response"""
    event_id: str
    event_title: str
    attendees_count: int
    attendees: List[AttendeeResponse]


@router.get("/getPaidTicketTypes", response_model=TicketTypesResponse, status_code=status.HTTP_200_OK)
async def get_paid_ticket_types(
    request: Request,
):
    print(f"[get_paid_ticket_types] Function called with event ID: {request.query_params.get('eventId')}")
    """Get all available paid ticket types for a given paid event
    
    This endpoint returns all available paid ticket types for a specific event,
    including details like price, description, and availability.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        A JSON response with event details and ticket types
    """
    event_id = request.query_params.get("eventId")
    if not event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event ID is required"
        )
    
    @sync_to_async
    def get_event_ticket_types(event_id):
        try:
            # Get the event
            event = Event.objects.get(eventId=event_id)
            
            # Check if this is a paid event
            if event.ticketing != "Paid":
                return {
                    "error": "This event does not have paid tickets"
                }
            
            # Get all ticket types for this event
            ticket_types = PaidFreeTicket.objects.filter(event=event)
            
            # Format the response
            ticket_types_data = []
            for ticket_type in ticket_types:
                available = ticket_type.ticket_quantity - ticket_type.ticket_sold
                ticket_types_data.append({
                    "ticket_id": str(ticket_type.ticket_id),
                    "ticket_name": ticket_type.ticket_name,
                    "ticket_price": float(ticket_type.ticket_price) if ticket_type.ticket_price else 0.0,
                    "ticket_description": ticket_type.ticket_description,
                    "ticket_quantity": ticket_type.ticket_quantity,
                    "ticket_sold": ticket_type.ticket_sold,
                    "available_tickets": available,
                    "crew_discounted_price": float(ticket_type.crew_discounted_price) if ticket_type.crew_discounted_price else None
                })
            
            return {
                "event_id": str(event.eventId),
                "event_title": event.title,
                "ticket_types": ticket_types_data
            }
            
        except Event.DoesNotExist:
            return {"error": "Event not found"}
        except Exception as e:
            import traceback
            print(f"Unexpected error in get_paid_ticket_types: {e}")
            print(traceback.format_exc())
            return {"error": str(e)}
    
    result = await get_event_ticket_types(event_id)
    
    if "error" in result:
        print(f"[get_paid_ticket_types] Error for event {event_id}: {result['error']}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if result["error"] == "Event not found" else status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    ticket_count = len(result.get('ticket_types', []))
    print(f"[get_paid_ticket_types] Successfully retrieved {ticket_count} ticket types for event: {event_id}")
    return result


@router.get("/getEventAttendees", response_model=AttendeesResponse, status_code=status.HTTP_200_OK)
async def get_event_attendees(
    request: Request
):
    """Get a list of users who have purchased a ticket for a specific event
    
    This endpoint returns a list of attendees for a specific event,
    including their personal information and ticket details.
    This endpoint is publicly accessible without authentication.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        A JSON response with event details and attendees list
    """
    event_id = request.query_params.get("eventId")
    if not event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event ID is required"
        )
    
    @sync_to_async
    def get_attendees_for_event(event_id):
        try:
            # Get the event
            event = Event.objects.get(eventId=event_id)
            
            # Get all tickets for this event with their related ticket types
            tickets = Ticket.objects.select_related('user', 'event').filter(event=event)
            
            # Format the response
            attendees_data = []
            for ticket in tickets:
                # Get the ticket type name if available
                ticket_type_name = "General Admission"  # Default value
                
                # Try to find the ticket type from the QR code data
                if ticket.qrCodeData:
                    try:
                        qr_data = json.loads(ticket.qrCodeData)
                        if 'ticketType' in qr_data:
                            ticket_type_name = qr_data['ticketType']
                    except json.JSONDecodeError:
                        pass
                
                attendees_data.append({
                    "ticket_id": str(ticket.ticketId),
                    "first_name": ticket.user.first_name if ticket.user else ticket.guestFirstName,
                    "last_name": ticket.user.last_name if ticket.user else ticket.guestLastName,
                    "email": ticket.user.email if ticket.user else ticket.guestEmail,
                    "ticket_type": ticket_type_name,
                    "purchase_date": ticket.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": ticket.status
                })
            
            return {
                "event_id": str(event.eventId),
                "event_title": event.title,
                "attendees_count": len(attendees_data),
                "attendees": attendees_data
            }
            
        except Event.DoesNotExist:
            return {"error": "Event not found"}

        except Exception as e:
            import traceback
            print(f"Unexpected error in get_event_attendees: {e}")
            print(traceback.format_exc())
            return {"error": str(e)}
    
    result = await get_attendees_for_event(event_id)
    
    if "error" in result:
        error_message = result["error"]
        print(f"[get_event_attendees] Error for event {event_id}: {error_message}")
        if error_message == "Event not found":
            status_code = status.HTTP_404_NOT_FOUND
        else:
            status_code = status.HTTP_400_BAD_REQUEST
            
        raise HTTPException(
            status_code=status_code,
            detail=error_message
        )
    
    print(f"[get_event_attendees] Successfully retrieved {result.get('attendees_count', 0)} attendees for event: {event_id}")
    return result


@router.get("/event/{eventId}/tickets", response_model=TicketTypesResponse, status_code=status.HTTP_200_OK)
async def get_tickets(eventId: str, user_id: Optional[int] = Depends(get_current_user)):
    """
    API endpoint to retrieve the types of tickets available for a specific event.
    
    This endpoint returns all available ticket types for a specific event,
    including details like price, description, and availability.
    
    Args:
        eventId: The ID of the event to get ticket types for
        user_id: The authenticated user ID (optional)
        
    Returns:
        A JSON response with event details and ticket types
    """
    print(f"[get_tickets API] Function called with eventId: {eventId}")
    
    @sync_to_async
    def get_event_ticket_types(event_id):
        try:
            # Get the event
            event = Event.objects.get(eventId=event_id)
            
            # Get all ticket types for this event
            ticket_types = PaidFreeTicket.objects.filter(event=event).select_related('event')
            
            # Format the response
            ticket_types_data = []
            for ticket_type in ticket_types:
                available = ticket_type.ticket_quantity - ticket_type.ticket_sold
                ticket_types_data.append({
                    "ticket_id": str(ticket_type.ticket_id),
                    "ticket_name": ticket_type.ticket_name,
                    "ticket_price": float(ticket_type.ticket_price) if ticket_type.ticket_price else 0.0,
                    "ticket_description": ticket_type.ticket_description,
                    "ticket_quantity": ticket_type.ticket_quantity,
                    "ticket_sold": ticket_type.ticket_sold,
                    "available_tickets": available,
                    "crew_discounted_price": float(ticket_type.crew_discounted_price) if ticket_type.crew_discounted_price else None
                })
            
            return {
                "event_id": str(event.eventId),
                "event_title": event.title,
                "ticket_types": ticket_types_data
            }
            
        except Event.DoesNotExist:
            return {"error": "Event not found"}
        except Exception as e:
            import traceback
            print(f"Unexpected error in get_tickets: {e}")
            print(traceback.format_exc())
            return {"error": str(e)}
    
    result = await get_event_ticket_types(eventId)
    
    if "error" in result:
        print(f"[get_tickets API] Error for event {eventId}: {result['error']}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if result["error"] == "Event not found" else status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    ticket_count = len(result.get('ticket_types', []))
    print(f"[get_tickets API] Successfully retrieved {ticket_count} ticket types for event: {eventId}")
    return result