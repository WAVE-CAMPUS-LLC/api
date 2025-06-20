from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from channels.db import database_sync_to_async
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
from eventTicketsApp.models import (
    Ticket,
    RSVPTicket,
    StripePlatformSettings,
    PaidFreeTicket,
)
from eventManagementApp.models import Event, CouponCode
from authenticationApp.models import CustomUser
from fastapi import Depends
from apiManager.dependencies import get_current_user
from eventTicketsApp.serializers import TicketSerializer
from socialApp.models import Crew


router = APIRouter()


# Helper functions for async Django ORM operations
async def get_event(event_id):
    """Get an event by ID asynchronously"""
    return await database_sync_to_async(Event.objects.get)(eventId=event_id)


async def get_host_id(event):
    """Get the host ID from an event asynchronously"""
    # We need to use a lambda to access the related field in a sync context
    return await database_sync_to_async(lambda: event.host.id)()


async def get_host(host_id):
    """Get a host by ID asynchronously"""
    return await database_sync_to_async(CustomUser.objects.get)(id=host_id)


async def get_platform_settings():
    """Get platform settings asynchronously"""
    settings = await database_sync_to_async(StripePlatformSettings.objects.first)()
    if not settings:
        settings = await database_sync_to_async(StripePlatformSettings.objects.create)()
    return settings


async def get_coupon(code, event):
    """Get a coupon by code and event asynchronously"""
    try:
        return await database_sync_to_async(CouponCode.objects.get)(
            code=code, event=event
        )
    except CouponCode.DoesNotExist:
        return None


async def get_user(user_id):
    """Get a user by ID asynchronously"""
    try:
        return await database_sync_to_async(CustomUser.objects.get)(id=user_id)
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


@router.post(
    "/processCheckout", response_model=CheckoutResponse, status_code=status.HTTP_200_OK
)
async def process_checkout(
    request: Request,
    cart_data: CartData = Body(...),
    user_id: Optional[int] = Depends(get_current_user),
):
    print(f"[DEBUG] ========== PROCESS CHECKOUT START ==========")
    print(f"[DEBUG] Function called with user_id: {user_id}")
    print(f"[DEBUG] Request method: {request.method}")
    print(f"[DEBUG] Request URL: {request.url}")
    print(f"[DEBUG] Request headers: {dict(request.headers)}")
    
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
    print(f"[DEBUG] Raw cart_data received: {cart_data}")
    print(f"[DEBUG] Extracted cart: {cart}")
    print(f"[DEBUG] Cart type: {type(cart)}")
    print(f"[DEBUG] Cart keys: {list(cart.keys()) if cart else 'None'}")

    if not cart:
        print(f"[DEBUG] ERROR: Cart is empty")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty"
        )

    print(f"[DEBUG] Cart validation passed - cart has {len(cart)} items")

    # Extract ticket items and calculate total amount
    print(f"[DEBUG] Starting ticket item extraction...")
    ticket_items = {
        k: v
        for k, v in cart.items()
        if k not in ["coupon_code", "discount_percentage"]
        and isinstance(v, dict)
        and "price" in v
        and "quantity" in v
    }

    print(f"[DEBUG] Extracted ticket items: {ticket_items}")
    print(f"[DEBUG] Number of ticket items found: {len(ticket_items)}")
    print(f"[DEBUG] Special cart items: {[k for k in cart.keys() if k in ['coupon_code', 'discount_percentage']]}")

    if not ticket_items:
        print(f"[DEBUG] ERROR: No valid tickets found in cart")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No valid tickets in cart"
        )

    # Validate ticket items
    print(f"[DEBUG] Starting ticket validation...")
    event_ids = set()
    for key, item in ticket_items.items():
        print(f"[DEBUG] Validating ticket {key}: {item}")
        
        # Validate price and quantity
        try:
            price = float(item.get("price", 0))
            quantity = int(item.get("quantity", 0))
            
            print(f"[DEBUG] Ticket {key} - Price: {price}, Quantity: {quantity}")
            
            if price < 0:
                print(f"[DEBUG] ERROR: Negative price for ticket {key}: {price}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"Invalid price for ticket {key}: price cannot be negative"
                )
            if quantity <= 0:
                print(f"[DEBUG] ERROR: Invalid quantity for ticket {key}: {quantity}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"Invalid quantity for ticket {key}: quantity must be greater than 0"
                )
        except (ValueError, TypeError) as e:
            print(f"[DEBUG] ERROR: Invalid price/quantity format for ticket {key}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Invalid price or quantity format for ticket {key}"
            )
        
        # Collect event IDs to ensure all tickets are from the same event
        event_id = item.get("eventId")
        print(f"[DEBUG] Ticket {key} eventId: {event_id}")
        
        if not event_id:
            print(f"[DEBUG] ERROR: Missing eventId for ticket {key}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Missing eventId for ticket {key}"
            )
        event_ids.add(event_id)

    print(f"[DEBUG] All event IDs found: {event_ids}")
    
    # Ensure all tickets are from the same event
    if len(event_ids) > 1:
        print(f"[DEBUG] ERROR: Multiple events found in cart: {event_ids}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="All tickets must be from the same event"
        )
    
    print(f"[DEBUG] Ticket validation passed - all tickets are from event: {list(event_ids)[0]}")

    # Calculate the total amount for tickets (without discount)
    print(f"[DEBUG] Starting total amount calculation...")
    total_amount = sum(
        float(item.get("price", 0)) * int(item.get("quantity", 0))
        for item in ticket_items.values()
    )
    print(f"[DEBUG] Total amount calculated: ${total_amount}")

    # Get event info from the first ticket
    first_ticket_key = next(iter(ticket_items.keys()))
    first_ticket = ticket_items[first_ticket_key]
    event_id = first_ticket.get("eventId")
    print(f"[DEBUG] Using event ID: {event_id} from first ticket: {first_ticket_key}")

    try:
        print(f"[DEBUG] Starting database operations...")
        
        # Get platform settings, event and host info
        print(f"[DEBUG] Fetching platform settings...")
        platform_settings = await get_platform_settings()
        print(f"[DEBUG] Platform settings retrieved: {platform_settings}")
        
        print(f"[DEBUG] Fetching event with ID: {event_id}")
        event = await get_event(event_id)
        print(f"[DEBUG] Event retrieved: {event}")
        
        print(f"[DEBUG] Fetching host ID for event...")
        host_id = await get_host_id(event)
        print(f"[DEBUG] Host ID: {host_id}")
        
        print(f"[DEBUG] Fetching host details...")
        host = await get_host(host_id)
        print(f"[DEBUG] Host retrieved: {host}")

        # Validate Stripe configuration
        print(f"[DEBUG] Validating Stripe configuration...")
        connect_account_id = await database_sync_to_async(
            lambda: host.connectAccountID
        )()
        print(f"[DEBUG] Connect account ID: {connect_account_id}")
        
        if not connect_account_id:
            print(f"[DEBUG] ERROR: Host has no connect account ID configured")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Event host has not configured payment processing"
            )
        
        print(f"[DEBUG] Stripe configuration validated successfully")

        # Process discount (from direct percentage or coupon code)
        print(f"[DEBUG] Starting discount processing...")
        discount_percentage = 0
        has_discount = False
        coupon_code_value = None

        # First check for direct discount percentage
        if "discount_percentage" in cart:
            print(f"[DEBUG] Found direct discount percentage in cart")
            try:
                discount_percentage = float(cart.get("discount_percentage"))
                print(f"[DEBUG] Parsed discount percentage: {discount_percentage}")
                
                if discount_percentage < 0 or discount_percentage > 100:
                    print(f"[DEBUG] ERROR: Invalid discount percentage range: {discount_percentage}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, 
                        detail="Discount percentage must be between 0 and 100"
                    )
                has_discount = True
                print(f"[DEBUG] Using discount percentage from cart: {discount_percentage}%")
                
            except (ValueError, TypeError) as e:
                print(f"[DEBUG] ERROR: Invalid discount percentage format: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Invalid discount percentage format"
                )
        # Then check for coupon code
        elif "coupon_code" in cart:
            print(f"[DEBUG] Found coupon code in cart")
            coupon_code_value = cart.get("coupon_code")
            print(f"[DEBUG] Coupon code value: {coupon_code_value}")
            
            if coupon_code_value:
                print(f"[DEBUG] Validating coupon code: {coupon_code_value}")
                coupon = await get_coupon(coupon_code_value, event)
                print(f"[DEBUG] Coupon lookup result: {coupon}")

                if coupon:
                    has_discount = True
                    discount_percentage = await database_sync_to_async(
                        lambda: coupon.discount_percentage
                    )()
                    print(f"[DEBUG] Valid coupon applied: {coupon_code_value}, Discount: {discount_percentage}%")
                else:
                    print(f"[DEBUG] ERROR: Invalid coupon code: {coupon_code_value}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, 
                        detail="Invalid coupon code"
                    )
        
        print(f"[DEBUG] Discount processing complete - Has discount: {has_discount}, Percentage: {discount_percentage}%")

        # Store original amount and apply discount
        print(f"[DEBUG] Starting amount calculations...")
        original_amount = total_amount
        original_amount_in_cents = int(original_amount * 100)
        print(f"[DEBUG] Original amount: ${original_amount} (${original_amount_in_cents} cents)")

        if has_discount and discount_percentage > 0:
            discount_amount = total_amount * (discount_percentage / 100)
            total_amount = total_amount - discount_amount
            print(f"[DEBUG] Applied {discount_percentage}% discount: Original: ${original_amount}, Discount: ${discount_amount}, New total: ${total_amount}")
        else:
            print(f"[DEBUG] No discount applied - using original amount: ${total_amount}")

        # Convert to cents after discount is applied
        amount_in_cents = int(total_amount * 100)
        print(f"[DEBUG] Final amount in cents: {amount_in_cents}")

        # Check for valid amount (allow zero for 100% discounts)
        if amount_in_cents < 0:
            print(f"[DEBUG] ERROR: Negative amount calculated: {amount_in_cents}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid amount calculation"
            )

        # Calculate service fee
        print(f"[DEBUG] Starting service fee calculation...")
        is_full_discount = (
            amount_in_cents <= 0 and has_discount and discount_percentage >= 100
        )
        print(f"[DEBUG] Is full discount: {is_full_discount}")
        
        if is_full_discount:
            # For 100% discounts, apply a minimal service fee based on the original price
            fee_amount = max(99, int(original_amount_in_cents * 0.07) + 99)
            print(f"[DEBUG] Full discount fee calculation: max(99, {int(original_amount_in_cents * 0.07)} + 99) = {fee_amount}")
        else:
            # 7% of discounted subtotal + $0.99 flat fee in cents
            fee_amount = int(amount_in_cents * 0.07) + 99
            print(f"[DEBUG] Regular fee calculation: {int(amount_in_cents * 0.07)} + 99 = {fee_amount}")

        print(f"[DEBUG] Service fee: ${fee_amount/100} calculated for {'100% discount' if is_full_discount else f'${total_amount} discounted amount'}")

        # Build Stripe line items
        print(f"[DEBUG] Building Stripe line items...")
        line_items = []
        for key, ticket in ticket_items.items():
            print(f"[DEBUG] Processing ticket {key}: {ticket}")
            
            # Calculate the discounted price for each ticket
            original_price = float(ticket["price"])
            print(f"[DEBUG] Original price for {key}: ${original_price}")

            # Apply discount if applicable
            if has_discount and discount_percentage > 0:
                discounted_price = original_price * (1 - discount_percentage / 100)
                unit_amount = int(Decimal(discounted_price) * 100)
                ticket_name = (
                    f"{ticket['name']} ({discount_percentage}% discount applied)"
                )
                print(f"[DEBUG] Discounted price for {key}: ${discounted_price} ({unit_amount} cents)")
            else:
                unit_amount = int(Decimal(original_price) * 100)
                ticket_name = ticket["name"]
                print(f"[DEBUG] No discount for {key}: ${original_price} ({unit_amount} cents)")

            # For 100% discounts, update the ticket name
            if unit_amount == 0 and is_full_discount:
                ticket_name = f"{ticket['name']} (100% discount applied)"
                print(f"[DEBUG] Updated ticket name for 100% discount: {ticket_name}")

            # Create metadata for the ticket
            metadata = {
                "original_ticket_name": ticket["name"],
                "original_ticket_id": key,
                "event_id": ticket.get("eventId"),
                "original_price": str(original_price),
            }

            if has_discount and discount_percentage > 0:
                metadata["is_discounted"] = "true"
                metadata["discount_percentage"] = str(discount_percentage)
                if coupon_code_value:
                    metadata["coupon_code"] = coupon_code_value

            print(f"[DEBUG] Ticket metadata for {key}: {metadata}")

            line_items.append(
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": ticket_name, "metadata": metadata},
                        "unit_amount": unit_amount,
                    },
                    "quantity": ticket["quantity"],
                }
            )
            print(f"[DEBUG] Added line item for {key}: {ticket_name} x{ticket['quantity']} at ${unit_amount/100} each")

        # Add service fee as a separate line item
        print(f"[DEBUG] Adding service fee line item...")
        line_items.append(
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Service Fee",
                        "metadata": {
                            "fee_type": "service_fee",
                            "is_full_discount": str(is_full_discount),
                        }
                    },
                    "unit_amount": fee_amount,
                },
                "quantity": 1,
            }
        )
        print(f"[DEBUG] Service fee line item added: ${fee_amount/100}")
        print(f"[DEBUG] Total line items: {len(line_items)}")

        try:
            print(f"[DEBUG] Creating Stripe checkout session with {len(line_items)} line items")

            # Get the current user if authenticated
            print(f"[DEBUG] Getting current user for user_id: {user_id}")
            current_user = await get_user(user_id) if user_id else None
            print(f"[DEBUG] Current user: {current_user}")

            # Get event information
            print(f"[DEBUG] Getting event information...")
            event_title = await database_sync_to_async(lambda: event.title)()
            event_id_str = await database_sync_to_async(lambda: str(event.eventId))()
            print(f"[DEBUG] Event title: {event_title}")
            print(f"[DEBUG] Event ID string: {event_id_str}")

            # Get the success and cancel URLs
            print(f"[DEBUG] Building payment URLs...")
            success_url = "https://waveoncampus.com/checkout/paymentSuccessful"
            cancel_url = "https://waveoncampus.com/checkout/paymentFailed"

            # Validate URLs
            if not success_url or not cancel_url:
                print(f"[DEBUG] ERROR: Payment URLs not configured properly")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Payment URLs not configured properly"
                )

            # Common session parameters
            print(f"[DEBUG] Building session parameters...")
            customer_id = (current_user.customer_id if current_user and hasattr(current_user, 'customer_id') else None)
            print(f"[DEBUG] Customer ID: {customer_id}")
            
            session_params = {
                "customer": customer_id,
                "payment_method_types": ["card"],
                "line_items": line_items,
                "mode": "payment",
                "success_url": f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
                "cancel_url": f"{cancel_url}",
                "metadata": {
                    "cart_data": json.dumps(cart),
                    "event_id": event_id_str,
                    "event_title": event_title,
                    "discount_percentage": (
                        str(discount_percentage) if has_discount else "0"
                    ),
                    "original_amount": str(original_amount),
                    "discounted_amount": str(total_amount),
                    "user_id": str(user_id) if user_id else "guest",
                },
            }
            print(f"[DEBUG] Session metadata: {session_params['metadata']}")

            # Add payment_intent_data with transfer for all checkouts (including 100% discount for service fee)
            print(f"[DEBUG] Setting up payment intent data...")
            total_transfer_amount = amount_in_cents if not is_full_discount else 0
            print(f"[DEBUG] Transfer amount: {total_transfer_amount} cents to {connect_account_id}")
            
            session_params["payment_intent_data"] = {
                "transfer_data": {
                    "destination": connect_account_id,
                    "amount": total_transfer_amount,
                },
                "metadata": {
                    "cart_data": json.dumps(cart),
                    "event_id": event_id_str,
                    "event_title": event_title,
                    "discount_percentage": (
                        str(discount_percentage) if has_discount else "0"
                    ),
                    "ticket_amount": str(amount_in_cents),
                    "fee_amount": str(fee_amount),
                    "is_full_discount": str(is_full_discount),
                },
            }
            print(f"[DEBUG] Payment intent metadata: {session_params['payment_intent_data']['metadata']}")

            print(f"[DEBUG] Creating Stripe checkout session...")
            checkout_session = stripe.checkout.Session.create(**session_params)

            print(f"[DEBUG] Checkout session created successfully: {checkout_session.id}")
            print(f"[DEBUG] Session URL: {checkout_session.url}")
            print(f"[DEBUG] ========== PROCESS CHECKOUT SUCCESS ==========")
            return {"sessionUrl": checkout_session.url}

        except stripe.error.StripeError as e:
            print(f"[DEBUG] ERROR: Stripe error occurred: {e}")
            print(f"[DEBUG] Stripe error type: {type(e)}")
            print(f"[DEBUG] ========== PROCESS CHECKOUT STRIPE ERROR ==========")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment processing error: {str(e)}",
            )

    except Event.DoesNotExist:
        print(f"[DEBUG] ERROR: Event not found with ID: {event_id}")
        print(f"[DEBUG] ========== PROCESS CHECKOUT EVENT ERROR ==========")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    except CustomUser.DoesNotExist:
        print(f"[DEBUG] ERROR: Host not found")
        print(f"[DEBUG] ========== PROCESS CHECKOUT HOST ERROR ==========")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Host not found"
        )
    except HTTPException as e:
        # Re-raise HTTP exceptions without modification
        print(f"[DEBUG] ERROR: HTTP Exception: {e.status_code} - {e.detail}")
        print(f"[DEBUG] ========== PROCESS CHECKOUT HTTP ERROR ==========")
        raise
    except Exception as e:
        import traceback

        print(f"[DEBUG] ERROR: Unexpected error in process_checkout: {e}")
        print(f"[DEBUG] ERROR: Exception type: {type(e)}")
        print(f"[DEBUG] ERROR: Full traceback:")
        print(traceback.format_exc())
        print(f"[DEBUG] ========== PROCESS CHECKOUT UNEXPECTED ERROR ==========")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An unexpected error occurred during checkout"
        )


@router.get("/ticketDetails")
async def ticket_details(request: Request):
    print(
        f"[ticket_details] Function called with ticket ID: {request.query_params.get('ticketId')}"
    )

    @database_sync_to_async
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
                        "building_name": event.building_name,
                    },
                },
                "status": ticket.status,
                "firstName": (
                    ticket.user.first_name if ticket.user else ticket.guestFirstName
                ),
                "lastName": (
                    ticket.user.last_name if ticket.user else ticket.guestLastName
                ),
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
    print(
        f"[activate_ticket] Function called with ticket ID: {request.query_params.get('ticketId')}"
    )

    @database_sync_to_async
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
            return {
                "valid": True,
                "message": "Ticket is activated",
                "ticketData": {
                    "ticketId": ticket.ticketId,
                    "event": {
                        "eventId": event.eventId,
                        "eventTitle": event.title,
                        "eventLocation": {
                            "street": event.street,
                            "city": event.city,
                            "state": event.state,
                            "zip_code": event.zip_code,
                            "building_name": event.building_name,
                        },
                    },
                    "status": ticket.status,
                },
            }
        except Ticket.DoesNotExist:
            return {"valid": False, "message": "Ticket not found"}
        except Exception as e:
            return {"valid": False, "message": f"An error occurred: {e}"}

    ticket_id = request.query_params.get("ticketId")
    result = await activate_user_ticket(ticket_id)
    print(
        f"[activate_ticket] Result for ticket {ticket_id}: {result.get('message', 'No message')}"
    )
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


@router.get(
    "/getPaidTicketTypes",
    response_model=TicketTypesResponse,
    status_code=status.HTTP_200_OK,
)
async def get_paid_ticket_types(
    request: Request,
):
    print(
        f"[get_paid_ticket_types] Function called with event ID: {request.query_params.get('eventId')}"
    )
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
            status_code=status.HTTP_400_BAD_REQUEST, detail="Event ID is required"
        )

    @database_sync_to_async
    def get_event_ticket_types(event_id):
        try:
            # Get the event
            event = Event.objects.get(eventId=event_id)

            # Check if this is a paid event
            if event.ticketing != "Paid":
                return {"error": "This event does not have paid tickets"}

            # Get all ticket types for this event
            ticket_types = PaidFreeTicket.objects.filter(event=event)

            # Format the response
            ticket_types_data = []
            for ticket_type in ticket_types:
                available = ticket_type.ticket_quantity - ticket_type.ticket_sold
                ticket_types_data.append(
                    {
                        "ticket_id": str(ticket_type.ticket_id),
                        "ticket_name": ticket_type.ticket_name,
                        "ticket_price": (
                            float(ticket_type.ticket_price)
                            if ticket_type.ticket_price
                            else 0.0
                        ),
                        "ticket_description": ticket_type.ticket_description,
                        "ticket_quantity": ticket_type.ticket_quantity,
                        "ticket_sold": ticket_type.ticket_sold,
                        "available_tickets": available,
                        "crew_discounted_price": (
                            float(ticket_type.crew_discounted_price)
                            if ticket_type.crew_discounted_price
                            else None
                        ),
                    }
                )

            return {
                "event_id": str(event.eventId),
                "event_title": event.title,
                "ticket_types": ticket_types_data,
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
            status_code=(
                status.HTTP_404_NOT_FOUND
                if result["error"] == "Event not found"
                else status.HTTP_400_BAD_REQUEST
            ),
            detail=result["error"],
        )

    ticket_count = len(result.get("ticket_types", []))
    print(
        f"[get_paid_ticket_types] Successfully retrieved {ticket_count} ticket types for event: {event_id}"
    )
    return result


@router.get(
    "/getEventAttendees",
    response_model=AttendeesResponse,
    status_code=status.HTTP_200_OK,
)
async def get_event_attendees(request: Request):
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
            status_code=status.HTTP_400_BAD_REQUEST, detail="Event ID is required"
        )

    @database_sync_to_async
    def get_attendees_for_event(event_id):
        try:
            # Get the event
            event = Event.objects.get(eventId=event_id)

            # Get all tickets for this event with their related ticket types
            tickets = Ticket.objects.select_related("user", "event").filter(event=event)

            # Format the response
            attendees_data = []
            for ticket in tickets:
                # Get the ticket type name if available
                ticket_type_name = "General Admission"  # Default value

                # Try to find the ticket type from the QR code data
                if ticket.qrCodeData:
                    try:
                        qr_data = json.loads(ticket.qrCodeData)
                        if "ticketType" in qr_data:
                            ticket_type_name = qr_data["ticketType"]
                    except json.JSONDecodeError:
                        pass

                attendees_data.append(
                    {
                        "ticket_id": str(ticket.ticketId),
                        "first_name": (
                            ticket.user.first_name
                            if ticket.user
                            else ticket.guestFirstName
                        ),
                        "last_name": (
                            ticket.user.last_name
                            if ticket.user
                            else ticket.guestLastName
                        ),
                        "email": (
                            ticket.user.email if ticket.user else ticket.guestEmail
                        ),
                        "ticket_type": ticket_type_name,
                        "purchase_date": ticket.created_at.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "status": ticket.status,
                    }
                )

            return {
                "event_id": str(event.eventId),
                "event_title": event.title,
                "attendees_count": len(attendees_data),
                "attendees": attendees_data,
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

        raise HTTPException(status_code=status_code, detail=error_message)

    print(
        f"[get_event_attendees] Successfully retrieved {result.get('attendees_count', 0)} attendees for event: {event_id}"
    )
    return result


@router.get(
    "/event/{eventId}/tickets",
    response_model=TicketTypesResponse,
    status_code=status.HTTP_200_OK,
)
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

    @database_sync_to_async
    def get_event_ticket_types(event_id):
        try:
            # Get the event
            event = Event.objects.get(eventId=event_id)

            # Get all ticket types for this event
            ticket_types = PaidFreeTicket.objects.filter(event=event).select_related(
                "event"
            )

            # Format the response
            ticket_types_data = []
            for ticket_type in ticket_types:
                available = ticket_type.ticket_quantity - ticket_type.ticket_sold
                ticket_types_data.append(
                    {
                        "ticket_id": str(ticket_type.ticket_id),
                        "ticket_name": ticket_type.ticket_name,
                        "ticket_price": (
                            float(ticket_type.ticket_price)
                            if ticket_type.ticket_price
                            else 0.0
                        ),
                        "ticket_description": ticket_type.ticket_description,
                        "ticket_quantity": ticket_type.ticket_quantity,
                        "ticket_sold": ticket_type.ticket_sold,
                        "available_tickets": available,
                        "crew_discounted_price": (
                            float(ticket_type.crew_discounted_price)
                            if ticket_type.crew_discounted_price
                            else None
                        ),
                    }
                )

            return {
                "event_id": str(event.eventId),
                "event_title": event.title,
                "ticket_types": ticket_types_data,
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
            status_code=(
                status.HTTP_404_NOT_FOUND
                if result["error"] == "Event not found"
                else status.HTTP_400_BAD_REQUEST
            ),
            detail=result["error"],
        )

    ticket_count = len(result.get("ticket_types", []))
    print(
        f"[get_tickets API] Successfully retrieved {ticket_count} ticket types for event: {eventId}"
    )
    return result


# Pydantic models for payment success API
class PaymentSuccessRequest(BaseModel):
    """Pydantic model for payment success request"""
    session_id: str
    from_mobile: Optional[bool] = False


class PaymentSuccessResponse(BaseModel):
    """Pydantic model for payment success response"""
    status: str
    tickets_generated: int
    duplicate: Optional[bool] = False
    message: Optional[str] = None


@router.post(
    "/paymentSuccessful",
    response_model=PaymentSuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def payment_successful(
    request: Request,
    payment_data: PaymentSuccessRequest = Body(...),
    user_id: Optional[int] = Depends(get_current_user),
):
    """
    API endpoint to handle successful payments and generate tickets.
    
    This endpoint processes successful Stripe payments, validates the session,
    prevents duplicate ticket generation, and creates tickets for the purchased items.
    
    Args:
        request: The FastAPI request object
        payment_data: The payment data containing session_id and mobile flag
        user_id: The authenticated user ID (optional)
        
    Returns:
        A JSON response with payment status and ticket generation details
    """
    print(f"[payment_successful API] Function called with session_id: {payment_data.session_id}")
    
    session_id = payment_data.session_id
    from_mobile = payment_data.from_mobile
    
    if not session_id or session_id == "{CHECKOUT_SESSION_ID}":
        print("Error: session_id is missing or invalid.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id is missing or invalid"
        )

    # Use database_sync_to_async wrapper for all Django ORM operations
    @database_sync_to_async
    def check_existing_tickets_and_process():
        """Check for existing tickets and process payment if needed"""
        from eventTicketsApp.views import generateTicket
        from django.db import transaction
        
        # Check if tickets have already been generated for this session
        print(f"[payment_successful API] Checking for tickets tied to session_id: {session_id}")
        existing_tickets = Ticket.objects.filter(stripe_session_id=session_id)
        
        if existing_tickets.exists():
            ticket_count = existing_tickets.count()
            print(f"Found {ticket_count} existing tickets for session {session_id}. Preventing duplicate generation.")
            return {
                "status": "paymentSuccessful", 
                "tickets_generated": ticket_count, 
                "duplicate": True
            }
        
        try:
            print(f"Retrieving Stripe session: {session_id}")
            session = stripe.checkout.Session.retrieve(session_id)
            
            # Use atomic transaction for ticket generation to ensure data consistency
            with transaction.atomic():
                # Reconstruct cart from Stripe session
                cart = _reconstruct_cart_from_stripe_sync(session)
                
                # Check if we still have an empty cart
                if not cart or len(cart) == 0 or all(k in ['coupon_code', 'discount_percentage'] for k in cart.keys()):
                    print("Warning: Cart is still empty after reconstruction attempt.")
                    # If cart reconstruction completely failed, we still need to create tickets based on the payment
                    # This can happen if the user paid but the cart metadata was corrupted
                    # In this case, we should still generate tickets based on what Stripe shows was paid for
                    ticket_line_items = [item for item in stripe.checkout.Session.list_line_items(session_id).data 
                                       if "Service Fee" not in item.description]
                    if ticket_line_items:
                        print(f"Creating minimal cart from {len(ticket_line_items)} line items due to cart reconstruction failure")
                        cart = {}  # Will be populated by fallback logic in ticket generation
                
                # Generate tickets from cart items
                ticket_count = _generate_tickets_from_cart_sync(user_id, cart, session_id, session)
                
                return {
                    "status": "paymentSuccessful", 
                    "tickets_generated": ticket_count
                }
            
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e}")
            raise Exception(f"Stripe error: {e}")
        except Exception as e:
            print(f"Error in payment processing: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Payment processing error: {str(e)}")
    
    try:
        result = await check_existing_tickets_and_process()
        print(f"[payment_successful API] Payment processing completed: {result}")
        return result
        
    except Exception as e:
        print(f"[payment_successful API] Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


def _reconstruct_cart_from_stripe_sync(session):
    """Synchronous version of cart reconstruction from Stripe session data"""
    cart = {}
    try:
        # Get line items from the session
        line_items = stripe.checkout.Session.list_line_items(
            session.id,
            expand=['data.price.product']  # Expand to get product metadata
        )
        print(f"Line items retrieved: {len(line_items.data)} items")
        
        # Get the payment intent to access metadata
        payment_intent = None
        if session.payment_intent:
            try:
                payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent)
                print(f"Retrieved payment intent: {payment_intent.id}")
            except Exception as e:
                print(f"Error retrieving payment intent: {e}")
        
        # First try to reconstruct from line items
        if line_items and line_items.data:
            cart = _extract_cart_from_line_items_sync(line_items.data)
        
        # If cart is still empty, try session metadata
        if not cart or all(k in ['coupon_code', 'discount_percentage'] for k in cart.keys()):
            cart = _extract_cart_from_metadata_sync(session, payment_intent, line_items)
            
        print(f"Final reconstructed cart: {json.dumps(cart, indent=2)}")
    except Exception as e:
        print(f"Error reconstructing cart from Stripe session: {e}")
        import traceback
        traceback.print_exc()
    
    return cart


def _extract_cart_from_line_items_sync(line_items):
    """Synchronous version of extracting cart data from Stripe line items"""
    cart = {}
    for item in line_items:
        # Skip service fee items
        if "Service Fee" in item.description:
            continue
        
        print(f"Processing line item: {item.description}, price: {item.amount_total/100}, quantity: {item.quantity}")
        
        # Try to get the original ticket info from metadata
        try:
            product = item.price.product
            if product and hasattr(product, 'metadata'):
                metadata = product.metadata
                original_ticket_id = metadata.get('original_ticket_id')
                event_id = metadata.get('event_id')
                
                if original_ticket_id and event_id:
                    try:
                        event = Event.objects.get(eventId=event_id)
                        
                        # Try to find the original ticket - original_ticket_id is the cart key, not the PaidFreeTicket.ticket_id
                        try:
                            # First try by ticket_id (UUID)
                            try:
                                ticket = PaidFreeTicket.objects.get(ticket_id=original_ticket_id, event=event)
                            except PaidFreeTicket.DoesNotExist:
                                # If not found, try by primary key (for cart keys that are database IDs)
                                ticket = PaidFreeTicket.objects.get(pk=original_ticket_id, event=event)
                            
                            cart[original_ticket_id] = {
                                "name": ticket.ticket_name,
                                "price": float(ticket.ticket_price),
                                "quantity": item.quantity,
                                "eventId": str(event.eventId)
                            }
                            continue
                        except Exception as e:
                            print(f"Error finding ticket with original_ticket_id={original_ticket_id}: {e}")
                            # Fallback: create cart item from line item data
                            cart[original_ticket_id] = {
                                "name": item.description.replace(" (100% discount applied)", "").replace(f" ({metadata.get('discount_percentage', 0)}% discount applied)", ""),
                                "price": item.amount_total / 100,
                                "quantity": item.quantity,
                                "eventId": str(event.eventId)
                            }
                    except (Event.DoesNotExist, PaidFreeTicket.DoesNotExist) as e:
                        print(f"Could not find original ticket/event: {e}")
        except Exception as e:
            print(f"Error accessing product metadata: {e}")
    
    return cart


def _extract_cart_from_metadata_sync(session, payment_intent, line_items):
    """Synchronous version of extracting cart data from session or payment intent metadata"""
    cart = {}
    try:
        # First try session metadata
        if hasattr(session, 'metadata') and session.metadata:
            cart_data = session.metadata.get('cart_data')
            if cart_data:
                try:
                    cart = json.loads(cart_data)
                    print("Successfully restored cart from session metadata")
                    return cart
                except json.JSONDecodeError:
                    print("Error decoding cart data from metadata")
        
        # If that fails, try payment intent metadata
        if not cart and payment_intent and payment_intent.metadata:
            cart_data = payment_intent.metadata.get('cart_data')
            if cart_data:
                try:
                    cart = json.loads(cart_data)
                    print("Successfully restored cart from payment intent metadata")
                    return cart
                except json.JSONDecodeError:
                    print("Error decoding cart data from payment intent metadata")
            
            # If we still don't have cart data, try to reconstruct from event ID
            if not cart:
                event_id = payment_intent.metadata.get('event_id')
                if event_id:
                    try:
                        event = Event.objects.get(eventId=event_id)
                        
                        # Create cart items from line items
                        for item in line_items.data:
                            if "Service Fee" not in item.description:
                                # Try to find the original ticket name without the discount note
                                original_name = item.description.replace(" (100% discount applied)", "")
                                tickets = PaidFreeTicket.objects.filter(
                                    event=event,
                                    ticket_name__iexact=original_name
                                )
                                
                                if tickets.exists():
                                    ticket = tickets.first()
                                    cart_key = str(ticket.id)
                                else:
                                    cart_key = f"stripe_item_{item.id}"
                                
                                cart[cart_key] = {
                                    "name": original_name,
                                    "price": item.amount_total / 100,
                                    "quantity": item.quantity,
                                    "eventId": str(event.eventId)
                                }
                    except Event.DoesNotExist:
                        print(f"Event with ID {event_id} from metadata not found")
    except Exception as e:
        print(f"Error trying to restore cart from metadata: {e}")
        import traceback
        traceback.print_exc()
    
    return cart


def _generate_tickets_from_cart_sync(user_id, cart, session_id, session):
    """Synchronous version of generating tickets from cart items"""
    from eventTicketsApp.views import generateTicket
    
    ticket_count = 0
    
    # Get the authenticated user if available
    user = None
    if user_id:
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            print(f"User with ID {user_id} not found")
    
    # Special handling for event_id if it's a direct key in the cart
    event_id_from_cart = cart.get('event_id')
    if event_id_from_cart and isinstance(event_id_from_cart, str):
        print(f"Found event_id directly in cart: {event_id_from_cart}")
    
    # If cart is empty or only has metadata, try to generate tickets from Stripe line items directly
    if not cart or all(k in ['coupon_code', 'discount_percentage', 'event_id'] for k in cart.keys()):
        print("Cart is empty or contains only metadata. Attempting fallback ticket generation from Stripe session.")
        ticket_count = _generate_tickets_from_stripe_session_sync(user_id, session_id, session)
        return ticket_count
    
    for cart_key, ticket_info in cart.items():
        # Skip non-ticket items
        if cart_key in ['coupon_code', 'discount_percentage', 'event_id', 'coupon_id']:
            continue
            
        # Check if ticket_info is a dictionary before trying to use .get()
        if not isinstance(ticket_info, dict):
            print(f"Warning: ticket_info for {cart_key} is not a dictionary: {type(ticket_info)}")
            continue
            
        # Get event_id from the ticket_info or use the one from the cart
        try:
            event_id = ticket_info.get("eventId") or event_id_from_cart
        except Exception as e:
            print(f"Error getting event ID: {e}")
            continue
            
        if not event_id:
            print(f"No event ID found in cart item {cart_key} or cart")
            continue
            
        try:
            event = Event.objects.get(eventId=event_id)
        except Event.DoesNotExist:
            print(f"Event with ID {event_id} not found.")
            continue

        # Handle crew tickets
        if "_crew_" in cart_key or "crewId" in ticket_info:
            ticket_count += _generate_crew_tickets_sync(user, ticket_info, event, session_id)
        else:
            # Handle regular tickets
            ticket_count += _generate_regular_tickets_sync(user, ticket_info, event, session_id, cart_key, session)
    
    print(f"Total tickets generated: {ticket_count}")
    return ticket_count


def _generate_crew_tickets_sync(user, ticket_info, event, session_id):
    """Synchronous version of generating tickets for crew members"""
    from eventTicketsApp.views import generateTicket
    
    ticket_count = 0
    crew_id = ticket_info.get("crewId")
    if not crew_id:
        print(f"No crew ID found in crew ticket")
        return ticket_count
        
    try:
        crew = Crew.objects.get(crewId=crew_id)
        print(f"Found crew: {crew.name} with {crew.members.count()} members")
        
        # Generate one ticket for each crew member
        for member in crew.members.all():
            try:
                ticket = generateTicket(
                    request=None,  # No request object in API context
                    event=event,
                    user=member if member else None,
                    guestFirstName=member.first_name if member else None,
                    guestLastName=member.last_name if member else None,
                    guestEmail=member.email if member else None,
                    crewTicket=(member != user),
                    stripe_session_id=session_id,
                    from_api=True
                )
                ticket_count += 1
                print(f"Generated crew ticket for {member.first_name} {member.last_name}")
            except Exception as e:
                print(f"Error generating crew ticket: {e}")
                import traceback
                traceback.print_exc()
    except Crew.DoesNotExist:
        print(f"Crew with ID {crew_id} not found.")
    
    return ticket_count


def _generate_regular_tickets_sync(user, ticket_info, event, session_id, cart_key, session):
    """Synchronous version of generating regular tickets"""
    from eventTicketsApp.views import generateTicket
    
    ticket_count = 0
    try:
        # Get customer information
        first_name, last_name, email = _get_customer_info_sync(user, session)
        
        # Generate tickets
        quantity = int(ticket_info.get("quantity", 1))
        print(f"Generating {quantity} tickets for {first_name} {last_name}")
        
        for i in range(quantity):
            ticket = generateTicket(
                request=None,  # No request object in API context
                event=event,
                user=user if user else None,
                guestFirstName=first_name,
                guestLastName=last_name,
                guestEmail=email,
                stripe_session_id=session_id,
                from_api=True
            )
            ticket_count += 1
            
            # Update the ticket_sold count in the PaidFreeTicket model
            _update_ticket_sold_count_sync(cart_key, event)
    except Exception as e:
        print(f"Error generating regular ticket: {e}")
        import traceback
        traceback.print_exc()
    
    return ticket_count


def _get_customer_info_sync(user, session):
    """Synchronous version of getting customer information from user or Stripe session"""
    if user:
        first_name = user.first_name
        last_name = user.last_name
        email = user.email
    else:
        # Get customer details from Stripe session
        first_name, last_name, email = "", "", ""
        if hasattr(session, 'customer_details') and session.customer_details:
            # Split the name on whitespace
            if hasattr(session.customer_details, 'name') and session.customer_details.name:
                name_parts = session.customer_details.name.split()
                first_name = name_parts[0] if name_parts else ""
                last_name = name_parts[-1] if len(name_parts) > 1 else ""
            
            email = session.customer_details.email if hasattr(session.customer_details, 'email') else ""
    
    return first_name, last_name, email


def _update_ticket_sold_count_sync(cart_key, event):
    """Synchronous version of updating the ticket_sold count in the PaidFreeTicket model"""
    try:
        # Find the ticket type and increment its sold count
        # Try by ticket_id first, then by primary key
        try:
            ticket_type = PaidFreeTicket.objects.get(ticket_id=cart_key, event=event)
        except PaidFreeTicket.DoesNotExist:
            # If not found by ticket_id, try by primary key (for cart keys that are database IDs)
            ticket_type = PaidFreeTicket.objects.get(pk=cart_key, event=event)
        
        ticket_type.ticket_sold += 1
        ticket_type.save()
        print(f"Updated ticket_sold count for {ticket_type.ticket_name}: now {ticket_type.ticket_sold}")
    except PaidFreeTicket.DoesNotExist:
        print(f"Could not find ticket type with cart_key {cart_key} for event {event.eventId}")
    except Exception as e:
        print(f"Error updating ticket_sold count: {e}")


def _generate_tickets_from_stripe_session_sync(user_id, session_id, session):
    """Fallback method to generate tickets directly from Stripe session when cart reconstruction fails"""
    from eventTicketsApp.views import generateTicket
    
    ticket_count = 0
    
    try:
        # Get line items from the session
        line_items = stripe.checkout.Session.list_line_items(session_id)
        
        # Get user if authenticated
        user = None
        if user_id:
            try:
                user = CustomUser.objects.get(id=user_id)
            except CustomUser.DoesNotExist:
                print(f"User with ID {user_id} not found")
        
        # Get customer info from session
        first_name, last_name, email = _get_customer_info_sync(user, session)
        
        # Get event from payment intent metadata
        event = None
        if session.payment_intent:
            try:
                payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent)
                event_id = payment_intent.metadata.get('event_id')
                if event_id:
                    event = Event.objects.get(eventId=event_id)
            except Exception as e:
                print(f"Error getting event from payment intent: {e}")
        
        if not event:
            print("Could not determine event for ticket generation")
            return 0
        
        # Generate tickets based on line items (excluding service fees)
        for item in line_items.data:
            if "Service Fee" not in item.description:
                # Generate tickets for this line item
                quantity = item.quantity
                for i in range(quantity):
                    ticket = generateTicket(
                        request=None,
                        event=event,
                        user=user if user else None,
                        guestFirstName=first_name,
                        guestLastName=last_name,
                        guestEmail=email,
                        stripe_session_id=session_id,
                        from_api=True
                    )
                    ticket_count += 1
                
                print(f"Generated {quantity} tickets from fallback method for {item.description}")
        
        print(f"Fallback ticket generation completed. Total tickets: {ticket_count}")
        return ticket_count
        
    except Exception as e:
        print(f"Error in fallback ticket generation: {e}")
        import traceback
        traceback.print_exc()
        return 0
