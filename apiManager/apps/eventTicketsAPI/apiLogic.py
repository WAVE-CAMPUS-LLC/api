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
from apiManager.utilities.notify_by_bot import notify_by_bot
from eventTicketsApp.models import (
    Ticket,
    RSVPTicket,
    StripePlatformSettings,
    PaidFreeTicket,
)
from eventManagementApp.models import Event, CouponCode
from authenticationApp.models import CustomUser
from apiManager.dependencies import get_current_user, get_current_user_optional
from eventTicketsApp.serializers import TicketSerializer
from socialApp.models import Crew
from apiManager.utilities.device_info import (
    get_comprehensive_request_info,
    create_enhanced_log_message,
)
from apiManager.utilities.device_info import get_device_info


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


async def get_current_user_object(
    user_id: Optional[int] = Depends(get_current_user_optional),
):
    """Get the current user object from the user_id returned by the dependency"""
    if user_id is None:
        return None
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

    checkout_url: str
    session_id: str
    amount: float
    fee_amount: float
    discount_percentage: float


@router.post(
    "/process_checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_200_OK,
)
async def process_checkout(
    request: Request,
    cart: Dict[str, Any] = Body(...),
    current_user: Optional[CustomUser] = Depends(get_current_user_object),
    platform: Optional[str] = None,
):
    """
    Process checkout and create Stripe checkout session for ticket purchase.

    Args:
        request: FastAPI request object
        cart: Dictionary containing ticket items and metadata
        current_user: Optional authenticated user
        platform: Optional platform identifier

    Returns:
        CheckoutResponse: Contains checkout session URL and metadata

    Raises:
        HTTPException: For various validation and processing errors
    """
    print(f"[process_checkout API] Function called with cart keys: {list(cart.keys())}")
    print(
        f"[process_checkout API] Current user: {current_user.id if current_user else 'None'}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        # Handle case where cart has an extra "cart" wrapper
        if len(cart) == 1 and "cart" in cart and isinstance(cart["cart"], dict):
            print(f"[DEBUG] Detected cart wrapper, extracting inner cart")
            cart = cart["cart"]
            print(f"[DEBUG] Extracted cart: {cart}")
        
        # Extract ticket items from cart (excluding metadata keys)
        ticket_items = {
            k: v
            for k, v in cart.items()
            if k not in ["coupon_code", "discount_percentage", "event_id"]
        }
        print(f"[DEBUG] Extracted ticket items: {ticket_items}")
        print(f"[DEBUG] Number of ticket items found: {len(ticket_items)}")
        print(
            f"[DEBUG] Special cart items: {[k for k in cart.keys() if k in ['coupon_code', 'discount_percentage']]}"
        )

        if not ticket_items:
            print(f"[DEBUG] ERROR: No ticket items found in cart")
            await notify_by_bot(
                f"**[API: process_checkout]** \n\n No ticket items found in cart \n\n Platform: {platform} \n\n User ID: {current_user.id if current_user else 'None'}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No ticket items found in cart",
            )

        # Validate ticket items
        event_ids = set()
        for key, ticket in ticket_items.items():
            try:
                original_price = float(ticket.get("price", 0))
                quantity = int(ticket.get("quantity", 0))
                event_id = ticket.get("eventId")

                if original_price < 0:
                    print(
                        f"[DEBUG] ERROR: Invalid price for ticket {key}: {original_price}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid price for ticket {key}: price cannot be negative",
                    )
                if quantity <= 0:
                    print(
                        f"[DEBUG] ERROR: Invalid quantity for ticket {key}: {quantity}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid quantity for ticket {key}: quantity must be greater than 0",
                    )
            except (ValueError, TypeError) as e:
                print(
                    f"[DEBUG] ERROR: Invalid price/quantity format for ticket {key}: {e}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid price or quantity format for ticket {key}",
                )

            if not event_id:
                print(f"[DEBUG] ERROR: Missing eventId for ticket {key}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing eventId for ticket {key}",
                )
            event_ids.add(event_id)

        # Ensure all tickets are from the same event
        if len(event_ids) > 1:
            print(f"[DEBUG] ERROR: Multiple events found: {event_ids}")
            await notify_by_bot(
                f"**[API: process_checkout]** \n\n Multiple events found in cart: {event_ids} \n\n Platform: {platform} \n\n User ID: {current_user.id if current_user else 'None'}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All tickets must be from the same event",
            )

        print(
            f"[DEBUG] Ticket validation passed - all tickets are from event: {list(event_ids)[0]}"
        )

        # Calculate the total amount for tickets (without discount)
        total_amount = sum(
            float(ticket.get("price", 0)) * int(ticket.get("quantity", 0))
            for ticket in ticket_items.values()
        )
        print(f"[DEBUG] Total amount before discount: ${total_amount}")

        # Process discounts
        has_discount = False
        discount_percentage = 0.0

        # First check for direct discount percentage in cart
        if "discount_percentage" in cart:
            try:
                discount_percentage = float(cart["discount_percentage"])
                if discount_percentage < 0 or discount_percentage > 100:
                    print(
                        f"[DEBUG] ERROR: Invalid discount percentage range: {discount_percentage}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Discount percentage must be between 0 and 100",
                    )
                has_discount = True
                print(
                    f"[DEBUG] Using discount percentage from cart: {discount_percentage}%"
                )

            except (ValueError, TypeError) as e:
                print(f"[DEBUG] ERROR: Invalid discount percentage format: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid discount percentage format",
                )
        # Then check for coupon code
        elif "coupon_code" in cart:
            coupon_code_value = cart["coupon_code"]
            if coupon_code_value:
                print(f"[DEBUG] Processing coupon code: {coupon_code_value}")
                try:
                    # Get the event
                    event = await database_sync_to_async(Event.objects.get)(eventId=list(event_ids)[0])

                    # Check if event has payment processing configured
                    host = await database_sync_to_async(lambda: event.host)()
                    if not host.connectAccountID:
                        print(
                            f"[DEBUG] ERROR: Event host has not configured payment processing"
                        )
                        await notify_by_bot(
                            f"**[API: process_checkout]** \n\n Event host has not configured payment processing: eventId={event.eventId} \n\n Platform: {platform} \n\n User ID: {current_user.id if current_user else 'None'}",
                            platform or "Unknown",
                            "ERROR",
                            device_info,
                        )
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Event host has not configured payment processing",
                        )

                    # Find the coupon
                    coupon = await database_sync_to_async(CouponCode.objects.get)(
                        coupon_code=coupon_code_value, event=event, is_active=True
                    )

                    # Apply the coupon discount
                    discount_percentage = await database_sync_to_async(
                        lambda: coupon.discount_percentage
                    )()
                    has_discount = True
                    print(
                        f"[DEBUG] Valid coupon applied: {coupon_code_value}, Discount: {discount_percentage}%"
                    )
                except CouponCode.DoesNotExist:
                    print(f"[DEBUG] ERROR: Invalid coupon code: {coupon_code_value}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid coupon code",
                    )
                except Event.DoesNotExist:
                    print(f"[DEBUG] ERROR: Event not found for coupon validation")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Event not found",
                    )
                except Exception as e:
                    print(f"[DEBUG] ERROR: Unexpected error processing coupon: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Error processing coupon code",
                    )

        print(
            f"[DEBUG] Discount processing complete - Has discount: {has_discount}, Percentage: {discount_percentage}%"
        )

        # Store original amount and apply discount
        print(f"[DEBUG] Starting amount calculations...")
        original_amount = total_amount
        original_amount_in_cents = int(original_amount * 100)
        print(
            f"[DEBUG] Original amount: ${original_amount} (${original_amount_in_cents} cents)"
        )

        if has_discount and discount_percentage > 0:
            discount_amount = total_amount * (discount_percentage / 100)
            total_amount = total_amount - discount_amount
            print(
                f"[DEBUG] Applied {discount_percentage}% discount: Original: ${original_amount}, Discount: ${discount_amount}, New total: ${total_amount}"
            )
        else:
            print(
                f"[DEBUG] No discount applied - using original amount: ${total_amount}"
            )

        # Convert to cents after discount is applied
        amount_in_cents = int(total_amount * 100)
        print(f"[DEBUG] Final amount in cents: {amount_in_cents}")

        # Validate final amount
        if amount_in_cents < 0:
            print(f"[DEBUG] ERROR: Negative amount calculated: {amount_in_cents}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid amount calculation",
            )

        # Calculate service fee
        is_full_discount = discount_percentage >= 100
        
        # If cart total is $0 before service fee, don't apply any service fee
        if amount_in_cents == 0:
            fee_amount = 0
            print(
                f"[DEBUG] Cart total is $0 - no service fee applied for completely free checkout"
            )
        elif is_full_discount:
            # For 100% discounts, apply a minimal service fee based on the original price
            fee_amount = max(99, int(original_amount_in_cents * 0.07) + 99)
            print(
                f"[DEBUG] Full discount fee calculation: max(99, {int(original_amount_in_cents * 0.07)} + 99) = {fee_amount}"
            )
        else:
            # 7% of discounted subtotal + $0.99 flat fee in cents
            fee_amount = int(amount_in_cents * 0.07) + 99
            print(
                f"[DEBUG] Regular fee calculation: {int(amount_in_cents * 0.07)} + 99 = {fee_amount}"
            )

        print(
            f"[DEBUG] Service fee: ${fee_amount/100} calculated for {'completely free checkout' if amount_in_cents == 0 else '100% discount' if is_full_discount else f'${total_amount} discounted amount'}"
        )

        # Build Stripe line items
        line_items = []
        for key, ticket in ticket_items.items():
            original_price = float(ticket.get("price", 0))
            quantity = int(ticket.get("quantity", 0))

            if has_discount and discount_percentage > 0:
                discounted_price = original_price * (1 - discount_percentage / 100)
                unit_amount = int(discounted_price * 100)
                ticket_name = (
                    f"{ticket['name']} ({discount_percentage}% discount applied)"
                )
                print(
                    f"[DEBUG] Discounted price for {key}: ${discounted_price} ({unit_amount} cents)"
                )
            else:
                unit_amount = int(Decimal(original_price) * 100)
                ticket_name = ticket["name"]
                print(
                    f"[DEBUG] No discount for {key}: ${original_price} ({unit_amount} cents)"
                )

            # For 100% discounts, update the ticket name
            if is_full_discount:
                ticket_name = f"{ticket['name']} (100% discount applied)"

            line_items.append(
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": ticket_name,
                            "metadata": {
                                "original_ticket_id": key,
                                "event_id": ticket.get("eventId"),
                                "discount_percentage": str(discount_percentage),
                                "original_price": str(original_price),
                                "is_full_discount": str(is_full_discount),
                            },
                        },
                        "unit_amount": unit_amount,
                    },
                    "quantity": quantity,
                }
            )
            print(
                f"[DEBUG] Added line item for {key}: {ticket_name} x{ticket['quantity']} at ${unit_amount/100} each"
            )

        # Add service fee as a separate line item (only if fee_amount > 0)
        if fee_amount > 0:
            line_items.append(
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": "Service Fee",
                            "metadata": {
                                "fee_type": "service_fee",
                                "is_full_discount": str(is_full_discount),
                            },
                        },
                        "unit_amount": fee_amount,
                    },
                    "quantity": 1,
                }
            )
            print(f"[DEBUG] Added service fee line item: ${fee_amount/100}")
        else:
            print(f"[DEBUG] No service fee line item added - completely free checkout")

        try:
            print(
                f"[DEBUG] Creating Stripe checkout session with {len(line_items)} line items"
            )

            # Get the current user if authenticated
            user_id = current_user.id if current_user else None
            print(f"[DEBUG] User ID for session: {user_id}")

            # Get the event and connect account
            event = await database_sync_to_async(Event.objects.get)(eventId=list(event_ids)[0])
            # Get the connect account ID from the event's host
            host = await database_sync_to_async(lambda: event.host)()
            connect_account_id = host.connectAccountID

            if not connect_account_id:
                print(f"[DEBUG] ERROR: No connect account found for event")
                await notify_by_bot(
                    f"**[API: process_checkout]** \n\n No connect account found for event: eventId={event.eventId} \n\n Platform: {platform} \n\n User ID: {current_user.id if current_user else 'None'}",
                    platform or "Unknown",
                    "ERROR",
                    device_info,
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Payment URLs not configured properly",
                )

            # Common session parameters
            print(f"[DEBUG] Building session parameters...")
            customer_id = (
                current_user.customer_id
                if current_user and hasattr(current_user, "customer_id")
                else None
            )
            print(f"[DEBUG] Customer ID: {customer_id}")

            session_params = {
                "line_items": line_items,
                "mode": "payment",
                "success_url": f"https://waveoncampus.com/checkout/paymentSuccessful?session_id={{CHECKOUT_SESSION_ID}}",
                "cancel_url": f"https://waveoncampus.com/checkout/paymentFailed",
                "metadata": {
                    "user_id": str(user_id) if user_id else "guest",
                    "event_id": str(event.eventId),
                    "cart_data": json.dumps(cart),
                    "platform": platform or "unknown",
                },
            }

            # Add customer if available
            if customer_id:
                session_params["customer"] = customer_id

            # Set up payment intent data for transfers (only if there's an amount to transfer)
            print(f"[DEBUG] Setting up payment intent data...")
            print(f"[DEBUG] Application fee amount: {fee_amount} cents")
            print(f"[DEBUG] Destination account: {connect_account_id}")
            print(f"[DEBUG] Total amount in cents: {amount_in_cents}")

            if amount_in_cents > 0 or fee_amount > 0:
                # Only set up payment intent data if there's money to transfer
                session_params["payment_intent_data"] = {
                    "metadata": {
                        "user_id": str(user_id) if user_id else "guest",
                        "event_id": str(event.eventId),
                        "cart_data": json.dumps(cart),
                        "platform": platform or "unknown",
                    },
                }
                
                # Only add application fee and transfer data if there's a fee or amount to transfer
                if fee_amount > 0:
                    session_params["payment_intent_data"]["application_fee_amount"] = fee_amount
                    
                if amount_in_cents > 0:
                    session_params["payment_intent_data"]["transfer_data"] = {
                        "destination": connect_account_id,
                    }
                
                print(f"[DEBUG] Payment intent configured for transfer")
            else:
                # For completely free checkouts, we still need metadata but no transfers
                session_params["metadata"]["user_id"] = str(user_id) if user_id else "guest"
                session_params["metadata"]["event_id"] = str(event.eventId)
                session_params["metadata"]["cart_data"] = json.dumps(cart)
                session_params["metadata"]["platform"] = platform or "unknown"
                session_params["metadata"]["is_free_checkout"] = "true"
                print(f"[DEBUG] Completely free checkout - no payment intent data needed")
            
            print(
                f"[DEBUG] Session configuration complete"
            )

            print(f"[DEBUG] Creating Stripe checkout session...")
            checkout_session = stripe.checkout.Session.create(**session_params)

            print(
                f"[DEBUG] Checkout session created successfully: {checkout_session.id}"
            )
            print(f"[DEBUG] Session URL: {checkout_session.url}")
            print(f"[DEBUG] ========== PROCESS CHECKOUT SUCCESS ==========")

            return CheckoutResponse(
                checkout_url=checkout_session.url,
                session_id=checkout_session.id,
                amount=total_amount,
                fee_amount=fee_amount / 100,
                discount_percentage=discount_percentage,
            )

        except stripe.error.StripeError as e:
            print(f"[DEBUG] Stripe error: {str(e)}")
            await notify_by_bot(
                f"**[API: process_checkout]** \n\n Stripe error: {str(e)} \n\n Platform: {platform} \n\n User ID: {current_user.id if current_user else 'None'}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment processing error: {str(e)}",
            )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"[DEBUG] Unexpected error: {str(e)}")
        await notify_by_bot(
            f"**[API: process_checkout]** \n\n Unexpected error: {str(e)} \n\n Platform: {platform} \n\n User ID: {current_user.id if current_user else 'None'}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during checkout",
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


@router.post("/payment_successful")
async def payment_successful(
    request: Request,
    payment_data: PaymentSuccessRequest,
    platform: Optional[str] = None,
):
    """
    API endpoint to handle successful payment and generate tickets.

    Args:
        request: FastAPI request object
        payment_data: Contains session_id from Stripe
        platform: Optional platform identifier

    Returns:
        A JSON response with payment status and ticket generation details
    """
    print(
        f"[payment_successful API] Function called with session_id: {payment_data.session_id}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    # Get comprehensive request information for enhanced logging
    request_info = get_comprehensive_request_info(request)
    
    print(create_enhanced_log_message("payment_successful API", "========== PAYMENT SUCCESS START ==========", request_info))
    print(create_enhanced_log_message("payment_successful API", f"Function called with session_id: {payment_data.session_id}", request_info))
    print(create_enhanced_log_message("payment_successful API", f"User ID: TBD (will extract from session)", request_info))
    print(create_enhanced_log_message("payment_successful API", f"From mobile: {payment_data.from_mobile}", request_info))
    print(create_enhanced_log_message("payment_successful API", f"Request method: {request.method}", request_info))
    print(create_enhanced_log_message("payment_successful API", f"Request URL: {request.url}", request_info))
    print(create_enhanced_log_message("payment_successful API", f"Client location: {request_info['location_string']}", request_info))
    print(create_enhanced_log_message("payment_successful API", f"Device info: {request_info['device_info']}", request_info))
    print(create_enhanced_log_message("payment_successful API", f"ISP: {request_info['isp']}", request_info))

    session_id = payment_data.session_id
    from_mobile = payment_data.from_mobile

    if not session_id or session_id == "{CHECKOUT_SESSION_ID}":
        print(
            create_enhanced_log_message(
                "payment_successful API",
                f"ERROR: session_id is missing or invalid: {session_id}",
                request_info,
            )
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id is missing or invalid",
        )

    print(
        create_enhanced_log_message(
            "payment_successful API",
            f"Session ID validation passed: {session_id}",
            request_info,
        )
    )

    # Use database_sync_to_async wrapper for all Django ORM operations
    @database_sync_to_async
    def check_existing_tickets_and_process():
        """Check for existing tickets and process payment if needed"""
        print(
            f"[check_existing_tickets_and_process] ========== STARTING TICKET PROCESSING =========="
        )
        from eventTicketsApp.views import generateTicket
        from django.db import transaction

        # Check if tickets have already been generated for this session
        print(
            f"[check_existing_tickets_and_process] Checking for existing tickets with session_id: {session_id}"
        )
        existing_tickets = Ticket.objects.filter(stripe_session_id=session_id)
        print(
            f"[check_existing_tickets_and_process] Query result: {existing_tickets.count()} existing tickets found"
        )

        if existing_tickets.exists():
            ticket_count = existing_tickets.count()
            print(
                f"[check_existing_tickets_and_process] DUPLICATE PREVENTION: Found {ticket_count} existing tickets for session {session_id}"
            )
            for ticket in existing_tickets:
                print(
                    f"[check_existing_tickets_and_process] Existing ticket: {ticket.ticketId} - {ticket.status}"
                )
            return {
                "status": "paymentSuccessful",
                "tickets_generated": ticket_count,
                "duplicate": True,
            }

        print(
            f"[check_existing_tickets_and_process] No existing tickets found. Proceeding with payment processing."
        )

        try:
            print(
                f"[check_existing_tickets_and_process] Retrieving Stripe session: {session_id}"
            )
            session = stripe.checkout.Session.retrieve(session_id)
            print(
                f"[check_existing_tickets_and_process] Stripe session retrieved successfully"
            )
            print(
                f"[check_existing_tickets_and_process] Session status: {session.payment_status}"
            )
            print(f"[check_existing_tickets_and_process] Session mode: {session.mode}")
            print(f"[check_existing_tickets_and_process] Customer: {session.customer}")
            print(
                f"[check_existing_tickets_and_process] Payment intent: {session.payment_intent}"
            )

            # Extract user ID from session metadata
            user_id = session.metadata.get("user_id")
            print(f"[check_existing_tickets_and_process] Extracted user_id from session metadata: {user_id}")
            
            if user_id and user_id != "guest":
                try:
                    user_id = int(user_id)
                    user = CustomUser.objects.get(id=user_id)
                    print(
                        f"[check_existing_tickets_and_process] Found authenticated user: {user.email}"
                    )
                except (ValueError, CustomUser.DoesNotExist):
                    print(
                        f"[check_existing_tickets_and_process] Invalid or non-existent user_id: {user_id}"
                    )
                    user_id = None
                    user = None
            else:
                print(f"[check_existing_tickets_and_process] Guest checkout detected")
                user_id = None
                user = None

            # Use atomic transaction for ticket generation to ensure data consistency
            print(
                f"[check_existing_tickets_and_process] Starting atomic transaction for ticket generation"
            )
            with transaction.atomic():
                # Reconstruct cart from Stripe session
                print(
                    f"[check_existing_tickets_and_process] Starting cart reconstruction from Stripe session"
                )
                cart = _reconstruct_cart_from_stripe_sync(session)
                print(
                    f"[check_existing_tickets_and_process] Cart reconstruction completed. Cart keys: {list(cart.keys()) if cart else 'None'}"
                )
                print(
                    f"[check_existing_tickets_and_process] Full reconstructed cart: {cart}"
                )

                # Check if we still have an empty cart
                if (
                    not cart
                    or len(cart) == 0
                    or all(
                        k in ["coupon_code", "discount_percentage"] for k in cart.keys()
                    )
                ):
                    print(
                        f"[check_existing_tickets_and_process] WARNING: Cart is empty after reconstruction attempt"
                    )
                    print(
                        f"[check_existing_tickets_and_process] Cart keys: {list(cart.keys()) if cart else 'None'}"
                    )
                    # If cart reconstruction completely failed, we still need to create tickets based on the payment
                    # This can happen if the user paid but the cart metadata was corrupted
                    # In this case, we should still generate tickets based on what Stripe shows was paid for
                    ticket_line_items = [
                        item
                        for item in stripe.checkout.Session.list_line_items(
                            session_id
                        ).data
                        if "Service Fee" not in item.description
                    ]
                    print(
                        f"[check_existing_tickets_and_process] Found {len(ticket_line_items)} non-service-fee line items"
                    )
                    if ticket_line_items:
                        print(
                            f"[check_existing_tickets_and_process] Creating minimal cart from {len(ticket_line_items)} line items due to cart reconstruction failure"
                        )
                        cart = (
                            {}
                        )  # Will be populated by fallback logic in ticket generation

                # Generate tickets from cart items
                print(
                    f"[check_existing_tickets_and_process] Starting ticket generation with user_id: {user_id}"
                )
                ticket_count = _generate_tickets_from_cart_sync(
                    user_id, cart, session_id, session
                )
                print(
                    f"[check_existing_tickets_and_process] Ticket generation completed. Total tickets: {ticket_count}"
                )

                return {
                    "status": "paymentSuccessful",
                    "tickets_generated": ticket_count,
                }

        except stripe.error.StripeError as e:
            print(f"[check_existing_tickets_and_process] STRIPE ERROR: {e}")
            print(f"[check_existing_tickets_and_process] Stripe error type: {type(e)}")
            raise Exception(f"Stripe error: {e}")
        except Exception as e:
            print(
                f"[check_existing_tickets_and_process] GENERAL ERROR in payment processing: {e}"
            )
            import traceback

            print(f"[check_existing_tickets_and_process] Full traceback:")
            traceback.print_exc()
            raise Exception(f"Payment processing error: {str(e)}")

    print(
        f"[payment_successful API] About to call check_existing_tickets_and_process()"
    )
    try:
        result = await check_existing_tickets_and_process()
        print(
            create_enhanced_log_message(
                "payment_successful API",
                f"Payment processing completed successfully: {result}",
                request_info,
            )
        )
        
        # Enhanced logging for email debugging
        if result.get("tickets_generated", 0) > 0:
            print(
                create_enhanced_log_message(
                    "payment_successful API",
                    f"Generated {result['tickets_generated']} tickets. Emails should have been sent to users.",
                    request_info,
                )
            )
            
            # Log email configuration for debugging
            from django.conf import settings
            print(
                create_enhanced_log_message(
                    "payment_successful API",
                    f"Email configuration - HOST: {getattr(settings, 'EMAIL_HOST', 'Not set')}, FROM: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not set')}",
                    request_info,
                )
            )
        
        print(
            create_enhanced_log_message(
                "payment_successful API",
                "========== PAYMENT SUCCESS END ==========",
                request_info,
            )
        )
        return result

    except Exception as e:
        print(
            create_enhanced_log_message(
                "payment_successful API",
                f"ERROR in payment_successful: {e}",
                request_info,
            )
        )
        print(
            create_enhanced_log_message(
                "payment_successful API", f"Error type: {type(e)}", request_info
            )
        )
        import traceback

        print(
            create_enhanced_log_message(
                "payment_successful API", "Full traceback:", request_info
            )
        )
        traceback.print_exc()
        print(
            create_enhanced_log_message(
                "payment_successful API",
                "========== PAYMENT SUCCESS ERROR END ==========",
                request_info,
            )
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def _reconstruct_cart_from_stripe_sync(session):
    """Synchronous version of cart reconstruction from Stripe session data"""
    print(
        f"[_reconstruct_cart_from_stripe_sync] ========== STARTING CART RECONSTRUCTION =========="
    )
    print(f"[_reconstruct_cart_from_stripe_sync] Session ID: {session.id}")
    print(
        f"[_reconstruct_cart_from_stripe_sync] Session payment status: {session.payment_status}"
    )
    cart = {}
    try:
        # Get line items from the session
        print(
            f"[_reconstruct_cart_from_stripe_sync] Retrieving line items from session"
        )
        line_items = stripe.checkout.Session.list_line_items(
            session.id, expand=["data.price.product"]  # Expand to get product metadata
        )
        print(
            f"[_reconstruct_cart_from_stripe_sync] Line items retrieved: {len(line_items.data)} items"
        )

        for i, item in enumerate(line_items.data):
            print(
                f"[_reconstruct_cart_from_stripe_sync] Line item {i}: {item.description}, quantity: {item.quantity}, amount: {item.amount_total/100}"
            )

        # Get the payment intent to access metadata
        payment_intent = None
        if session.payment_intent:
            print(
                f"[_reconstruct_cart_from_stripe_sync] Retrieving payment intent: {session.payment_intent}"
            )
            try:
                payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent)
                print(
                    f"[_reconstruct_cart_from_stripe_sync] Payment intent retrieved: {payment_intent.id}"
                )
                print(
                    f"[_reconstruct_cart_from_stripe_sync] Payment intent metadata: {payment_intent.metadata}"
                )
            except Exception as e:
                print(
                    f"[_reconstruct_cart_from_stripe_sync] Error retrieving payment intent: {e}"
                )
        else:
            print(
                f"[_reconstruct_cart_from_stripe_sync] No payment intent found in session"
            )

        # First try to reconstruct from line items
        print(
            f"[_reconstruct_cart_from_stripe_sync] Attempting cart reconstruction from line items"
        )
        if line_items and line_items.data:
            cart = _extract_cart_from_line_items_sync(line_items.data)
            print(f"[_reconstruct_cart_from_stripe_sync] Cart from line items: {cart}")
        else:
            print(f"[_reconstruct_cart_from_stripe_sync] No line items found")

        # If cart is still empty, try session metadata
        if not cart or all(
            k in ["coupon_code", "discount_percentage"] for k in cart.keys()
        ):
            print(
                f"[_reconstruct_cart_from_stripe_sync] Cart empty from line items, trying metadata reconstruction"
            )
            cart = _extract_cart_from_metadata_sync(session, payment_intent, line_items)
            print(f"[_reconstruct_cart_from_stripe_sync] Cart from metadata: {cart}")
        else:
            print(
                f"[_reconstruct_cart_from_stripe_sync] Cart successfully reconstructed from line items"
            )

        print(
            f"[_reconstruct_cart_from_stripe_sync] Final reconstructed cart: {json.dumps(cart, indent=2)}"
        )
        print(f"[_reconstruct_cart_from_stripe_sync] Cart keys: {list(cart.keys())}")
        print(
            f"[_reconstruct_cart_from_stripe_sync] ========== CART RECONSTRUCTION COMPLETE =========="
        )
    except Exception as e:
        print(
            f"[_reconstruct_cart_from_stripe_sync] ERROR reconstructing cart from Stripe session: {e}"
        )
        import traceback

        print(f"[_reconstruct_cart_from_stripe_sync] Full traceback:")
        traceback.print_exc()
        print(
            f"[_reconstruct_cart_from_stripe_sync] ========== CART RECONSTRUCTION ERROR =========="
        )

    return cart


def _extract_cart_from_line_items_sync(line_items):
    """Synchronous version of extracting cart data from Stripe line items"""
    print(
        f"[_extract_cart_from_line_items_sync] ========== STARTING LINE ITEMS EXTRACTION =========="
    )
    print(
        f"[_extract_cart_from_line_items_sync] Processing {len(line_items)} line items"
    )
    cart = {}

    for i, item in enumerate(line_items):
        print(
            f"[_extract_cart_from_line_items_sync] Processing line item {i}: {item.description}"
        )

        # Skip service fee items
        if "Service Fee" in item.description:
            print(
                f"[_extract_cart_from_line_items_sync] Skipping service fee item: {item.description}"
            )
            continue

        print(
            f"[_extract_cart_from_line_items_sync] Line item details - Description: {item.description}, Price: {item.amount_total/100}, Quantity: {item.quantity}"
        )

        # Try to get the original ticket info from metadata
        try:
            product = item.price.product
            print(f"[_extract_cart_from_line_items_sync] Product: {product}")
            if product and hasattr(product, "metadata"):
                metadata = product.metadata
                print(
                    f"[_extract_cart_from_line_items_sync] Product metadata: {metadata}"
                )
                original_ticket_id = metadata.get("original_ticket_id")
                event_id = metadata.get("event_id")
                print(
                    f"[_extract_cart_from_line_items_sync] Original ticket ID: {original_ticket_id}, Event ID: {event_id}"
                )

                if original_ticket_id and event_id:
                    try:
                        print(
                            f"[_extract_cart_from_line_items_sync] Looking up event with ID: {event_id}"
                        )
                        event = Event.objects.get(eventId=event_id)
                        print(
                            f"[_extract_cart_from_line_items_sync] Event found: {event.title}"
                        )

                        # Try to find the original ticket - original_ticket_id is the cart key, not necessarily the PaidFreeTicket.ticket_id
                        try:
                            # First try by ticket_id (UUID) - but handle validation errors
                            print(
                                f"[_extract_cart_from_line_items_sync] Trying to find PaidFreeTicket by ticket_id: {original_ticket_id}"
                            )
                            ticket = None

                            # Check if original_ticket_id looks like a UUID
                            try:
                                import uuid

                                # Try to parse as UUID to validate format
                                uuid.UUID(original_ticket_id)
                                # If it's a valid UUID, try to find by ticket_id
                                ticket = PaidFreeTicket.objects.get(
                                    ticket_id=original_ticket_id, event=event
                                )
                                print(
                                    f"[_extract_cart_from_line_items_sync] Found ticket by ticket_id: {ticket.ticket_name}"
                                )
                            except (ValueError, PaidFreeTicket.DoesNotExist):
                                # If not a valid UUID or not found by UUID, try by primary key if it's numeric
                                try:
                                    # Try to find by primary key (for cart keys that are database IDs)
                                    print(
                                        f"[_extract_cart_from_line_items_sync] Not found by ticket_id, trying by primary key: {original_ticket_id}"
                                    )
                                    # For non-UUID cart keys, try to find ticket by name match
                                    tickets = PaidFreeTicket.objects.filter(event=event)
                                    ticket_name_from_metadata = metadata.get(
                                        "original_ticket_name", item.description
                                    )
                                    for t in tickets:
                                        if t.ticket_name == ticket_name_from_metadata:
                                            ticket = t
                                            print(
                                                f"[_extract_cart_from_line_items_sync] Found ticket by name match: {ticket.ticket_name}"
                                            )
                                            break
                                except Exception as inner_e:
                                    print(
                                        f"[_extract_cart_from_line_items_sync] Error in fallback lookup: {inner_e}"
                                    )

                            if ticket:
                                cart_item = {
                                    "name": ticket.ticket_name,
                                    "price": float(ticket.ticket_price),
                                    "quantity": item.quantity,
                                    "eventId": str(event.eventId),
                                }
                                cart[original_ticket_id] = cart_item
                                print(
                                    f"[_extract_cart_from_line_items_sync] Added cart item: {original_ticket_id} -> {cart_item}"
                                )
                                continue
                            else:
                                raise Exception("Ticket not found")

                        except Exception as e:
                            print(
                                f"[_extract_cart_from_line_items_sync] Error finding ticket with original_ticket_id={original_ticket_id}: {e}"
                            )
                            # Fallback: create cart item from line item data
                            fallback_item = {
                                "name": item.description.replace(
                                    " (100% discount applied)", ""
                                ).replace(
                                    f" ({metadata.get('discount_percentage', 0)}% discount applied)",
                                    "",
                                ),
                                "price": item.amount_total / 100,
                                "quantity": item.quantity,
                                "eventId": str(event.eventId),
                            }
                            cart[original_ticket_id] = fallback_item
                            print(
                                f"[_extract_cart_from_line_items_sync] Added fallback cart item: {original_ticket_id} -> {fallback_item}"
                            )
                    except (Event.DoesNotExist, PaidFreeTicket.DoesNotExist) as e:
                        print(
                            f"[_extract_cart_from_line_items_sync] Could not find original ticket/event: {e}"
                        )
                else:
                    print(
                        f"[_extract_cart_from_line_items_sync] Missing original_ticket_id or event_id in metadata"
                    )
            else:
                print(
                    f"[_extract_cart_from_line_items_sync] No product or metadata found for line item"
                )
        except Exception as e:
            print(
                f"[_extract_cart_from_line_items_sync] Error accessing product metadata: {e}"
            )
            import traceback

            print(f"[_extract_cart_from_line_items_sync] Traceback:")
            traceback.print_exc()

    print(f"[_extract_cart_from_line_items_sync] Final cart from line items: {cart}")
    print(
        f"[_extract_cart_from_line_items_sync] ========== LINE ITEMS EXTRACTION COMPLETE =========="
    )
    return cart


def _extract_cart_from_metadata_sync(session, payment_intent, line_items):
    """Synchronous version of extracting cart data from session or payment intent metadata"""
    print(
        f"[_extract_cart_from_metadata_sync] ========== STARTING METADATA EXTRACTION =========="
    )
    cart = {}
    try:
        # First try session metadata
        print(f"[_extract_cart_from_metadata_sync] Checking session metadata")
        if hasattr(session, "metadata") and session.metadata:
            print(
                f"[_extract_cart_from_metadata_sync] Session metadata found: {session.metadata}"
            )
            cart_data = session.metadata.get("cart_data")
            if cart_data:
                print(
                    f"[_extract_cart_from_metadata_sync] Cart data found in session metadata: {cart_data[:200]}..."
                )
                try:
                    cart = json.loads(cart_data)
                    print(
                        f"[_extract_cart_from_metadata_sync] Successfully restored cart from session metadata: {cart}"
                    )
                    return cart
                except json.JSONDecodeError as e:
                    print(
                        f"[_extract_cart_from_metadata_sync] Error decoding cart data from session metadata: {e}"
                    )
            else:
                print(
                    f"[_extract_cart_from_metadata_sync] No cart_data found in session metadata"
                )
        else:
            print(f"[_extract_cart_from_metadata_sync] No session metadata found")

        # If that fails, try payment intent metadata
        print(f"[_extract_cart_from_metadata_sync] Checking payment intent metadata")
        if not cart and payment_intent and payment_intent.metadata:
            print(
                f"[_extract_cart_from_metadata_sync] Payment intent metadata found: {payment_intent.metadata}"
            )
            cart_data = payment_intent.metadata.get("cart_data")
            if cart_data:
                print(
                    f"[_extract_cart_from_metadata_sync] Cart data found in payment intent metadata: {cart_data[:200]}..."
                )
                try:
                    cart = json.loads(cart_data)
                    print(
                        f"[_extract_cart_from_metadata_sync] Successfully restored cart from payment intent metadata: {cart}"
                    )
                    return cart
                except json.JSONDecodeError as e:
                    print(
                        f"[_extract_cart_from_metadata_sync] Error decoding cart data from payment intent metadata: {e}"
                    )
            else:
                print(
                    f"[_extract_cart_from_metadata_sync] No cart_data found in payment intent metadata"
                )

            # If we still don't have cart data, try to reconstruct from event ID
            if not cart:
                print(
                    f"[_extract_cart_from_metadata_sync] Attempting reconstruction from event ID"
                )
                event_id = payment_intent.metadata.get("event_id")
                print(
                    f"[_extract_cart_from_metadata_sync] Event ID from payment intent: {event_id}"
                )
                if event_id:
                    try:
                        print(
                            f"[_extract_cart_from_metadata_sync] Looking up event with ID: {event_id}"
                        )
                        event = Event.objects.get(eventId=event_id)
                        print(
                            f"[_extract_cart_from_metadata_sync] Event found: {event.title}"
                        )

                        # Create cart items from line items
                        print(
                            f"[_extract_cart_from_metadata_sync] Creating cart items from line items"
                        )
                        for i, item in enumerate(line_items.data):
                            if "Service Fee" not in item.description:
                                print(
                                    f"[_extract_cart_from_metadata_sync] Processing line item {i}: {item.description}"
                                )
                                # Try to find the original ticket name without the discount note
                                original_name = item.description.replace(
                                    " (100% discount applied)", ""
                                )
                                print(
                                    f"[_extract_cart_from_metadata_sync] Original name after discount removal: {original_name}"
                                )
                                tickets = PaidFreeTicket.objects.filter(
                                    event=event, ticket_name__iexact=original_name
                                )
                                print(
                                    f"[_extract_cart_from_metadata_sync] Found {tickets.count()} matching tickets"
                                )

                                if tickets.exists():
                                    ticket = tickets.first()
                                    cart_key = str(ticket.id)
                                    print(
                                        f"[_extract_cart_from_metadata_sync] Using ticket ID as cart key: {cart_key}"
                                    )
                                else:
                                    cart_key = f"stripe_item_{item.id}"
                                    print(
                                        f"[_extract_cart_from_metadata_sync] Using fallback cart key: {cart_key}"
                                    )

                                cart_item = {
                                    "name": original_name,
                                    "price": item.amount_total / 100,
                                    "quantity": item.quantity,
                                    "eventId": str(event.eventId),
                                }
                                cart[cart_key] = cart_item
                                print(
                                    f"[_extract_cart_from_metadata_sync] Added cart item: {cart_key} -> {cart_item}"
                                )
                    except Event.DoesNotExist:
                        print(
                            f"[_extract_cart_from_metadata_sync] Event with ID {event_id} from metadata not found"
                        )
                else:
                    print(
                        f"[_extract_cart_from_metadata_sync] No event_id found in payment intent metadata"
                    )
        else:
            print(
                f"[_extract_cart_from_metadata_sync] No payment intent or payment intent metadata found"
            )
    except Exception as e:
        print(
            f"[_extract_cart_from_metadata_sync] Error trying to restore cart from metadata: {e}"
        )
        import traceback

        print(f"[_extract_cart_from_metadata_sync] Full traceback:")
        traceback.print_exc()

    print(f"[_extract_cart_from_metadata_sync] Final cart from metadata: {cart}")
    print(
        f"[_extract_cart_from_metadata_sync] ========== METADATA EXTRACTION COMPLETE =========="
    )
    return cart


def _generate_tickets_from_cart_sync(user_id, cart, session_id, session):
    """Synchronous version of generating tickets from cart items"""
    print(
        f"[_generate_tickets_from_cart_sync] ========== STARTING TICKET GENERATION =========="
    )
    print(f"[_generate_tickets_from_cart_sync] User ID: {user_id}")
    print(f"[_generate_tickets_from_cart_sync] Session ID: {session_id}")
    print(f"[_generate_tickets_from_cart_sync] Cart: {cart}")
    print(
        f"[_generate_tickets_from_cart_sync] Cart keys: {list(cart.keys()) if cart else 'None'}"
    )

    from eventTicketsApp.views import generateTicket

    ticket_count = 0

    # Get the authenticated user if available
    user = None
    if user_id:
        print(f"[_generate_tickets_from_cart_sync] Looking up user with ID: {user_id}")
        try:
            user = CustomUser.objects.get(id=user_id)
            print(
                f"[_generate_tickets_from_cart_sync] User found: {user.username} ({user.email})"
            )
        except CustomUser.DoesNotExist:
            print(
                f"[_generate_tickets_from_cart_sync] User with ID {user_id} not found"
            )
    else:
        print(
            f"[_generate_tickets_from_cart_sync] No user ID provided (guest checkout)"
        )

    # Special handling for event_id if it's a direct key in the cart
    event_id_from_cart = cart.get("event_id")
    if event_id_from_cart and isinstance(event_id_from_cart, str):
        print(
            f"[_generate_tickets_from_cart_sync] Found event_id directly in cart: {event_id_from_cart}"
        )
    else:
        print(f"[_generate_tickets_from_cart_sync] No event_id found directly in cart")

    # If cart is empty or only has metadata, try to generate tickets from Stripe line items directly
    if not cart or all(
        k in ["coupon_code", "discount_percentage", "event_id"] for k in cart.keys()
    ):
        print(
            f"[_generate_tickets_from_cart_sync] Cart is empty or contains only metadata. Attempting fallback ticket generation from Stripe session."
        )
        ticket_count = _generate_tickets_from_stripe_session_sync(
            user_id, session_id, session
        )
        print(
            f"[_generate_tickets_from_cart_sync] Fallback generation returned {ticket_count} tickets"
        )
        return ticket_count

    print(f"[_generate_tickets_from_cart_sync] Processing {len(cart)} cart items")
    for cart_key, ticket_info in cart.items():
        print(
            f"[_generate_tickets_from_cart_sync] Processing cart item: {cart_key} -> {ticket_info}"
        )

        # Skip non-ticket items
        if cart_key in ["coupon_code", "discount_percentage", "event_id", "coupon_id"]:
            print(
                f"[_generate_tickets_from_cart_sync] Skipping metadata item: {cart_key}"
            )
            continue

        # Check if ticket_info is a dictionary before trying to use .get()
        if not isinstance(ticket_info, dict):
            print(
                f"[_generate_tickets_from_cart_sync] Warning: ticket_info for {cart_key} is not a dictionary: {type(ticket_info)}"
            )
            continue

        # Get event_id from the ticket_info or use the one from the cart
        try:
            event_id = ticket_info.get("eventId") or event_id_from_cart
            print(
                f"[_generate_tickets_from_cart_sync] Event ID for {cart_key}: {event_id}"
            )
        except Exception as e:
            print(
                f"[_generate_tickets_from_cart_sync] Error getting event ID for {cart_key}: {e}"
            )
            continue

        if not event_id:
            print(
                f"[_generate_tickets_from_cart_sync] No event ID found in cart item {cart_key} or cart"
            )
            continue

        try:
            print(
                f"[_generate_tickets_from_cart_sync] Looking up event with ID: {event_id}"
            )
            event = Event.objects.get(eventId=event_id)
            print(f"[_generate_tickets_from_cart_sync] Event found: {event.title}")
        except Event.DoesNotExist:
            print(
                f"[_generate_tickets_from_cart_sync] Event with ID {event_id} not found."
            )
            continue

        # Handle crew tickets
        if "_crew_" in cart_key or "crewId" in ticket_info:
            print(
                f"[_generate_tickets_from_cart_sync] Generating crew tickets for {cart_key}"
            )
            crew_ticket_count = _generate_crew_tickets_sync(
                user, ticket_info, event, session_id
            )
            ticket_count += crew_ticket_count
            print(
                f"[_generate_tickets_from_cart_sync] Generated {crew_ticket_count} crew tickets"
            )
        else:
            # Handle regular tickets
            print(
                f"[_generate_tickets_from_cart_sync] Generating regular tickets for {cart_key}"
            )
            regular_ticket_count = _generate_regular_tickets_sync(
                user, ticket_info, event, session_id, cart_key, session
            )
            ticket_count += regular_ticket_count
            print(
                f"[_generate_tickets_from_cart_sync] Generated {regular_ticket_count} regular tickets"
            )

    print(f"[_generate_tickets_from_cart_sync] Total tickets generated: {ticket_count}")
    print(
        f"[_generate_tickets_from_cart_sync] ========== TICKET GENERATION COMPLETE =========="
    )
    return ticket_count


def _generate_crew_tickets_sync(user, ticket_info, event, session_id):
    """Synchronous version of generating tickets for crew members"""
    print(
        f"[_generate_crew_tickets_sync] ========== STARTING CREW TICKET GENERATION =========="
    )
    print(f"[_generate_crew_tickets_sync] User: {user}")
    print(f"[_generate_crew_tickets_sync] Ticket info: {ticket_info}")
    print(f"[_generate_crew_tickets_sync] Event: {event.title} ({event.eventId})")
    print(f"[_generate_crew_tickets_sync] Session ID: {session_id}")

    from eventTicketsApp.views import generateTicket

    ticket_count = 0
    crew_id = ticket_info.get("crewId")
    print(f"[_generate_crew_tickets_sync] Crew ID from ticket info: {crew_id}")

    if not crew_id:
        print(f"[_generate_crew_tickets_sync] No crew ID found in crew ticket")
        return ticket_count

    try:
        print(f"[_generate_crew_tickets_sync] Looking up crew with ID: {crew_id}")
        crew = Crew.objects.get(crewId=crew_id)
        print(
            f"[_generate_crew_tickets_sync] Found crew: {crew.name} with {crew.members.count()} members"
        )

        # Generate one ticket for each crew member
        for i, member in enumerate(crew.members.all()):
            print(
                f"[_generate_crew_tickets_sync] Processing crew member {i+1}: {member.first_name} {member.last_name} ({member.email})"
            )
            try:
                # Create a comprehensive mock request object for email functionality
                from django.http import HttpRequest
                from django.contrib.auth.models import AnonymousUser
                mock_request = HttpRequest()
                mock_request.META['HTTP_HOST'] = 'waveoncampus.com'
                mock_request.META['wsgi.url_scheme'] = 'https'
                mock_request.META['SERVER_NAME'] = 'waveoncampus.com'
                mock_request.META['SERVER_PORT'] = '443'
                mock_request.is_secure = lambda: True
                mock_request.user = user if user else AnonymousUser()
                mock_request.method = 'POST'
                
                # Validate email before ticket generation
                validated_email, validated_first, validated_last, email_valid = _ensure_email_delivery(
                    member, member.email if member else None, 
                    member.first_name if member else None, 
                    member.last_name if member else None
                )
                
                ticket = generateTicket(
                    request=mock_request,
                    event=event,
                    user=member if member else None,
                    guestFirstName=validated_first,
                    guestLastName=validated_last,
                    guestEmail=validated_email,
                    crewTicket=(member != user),
                    stripe_session_id=session_id,
                    from_api=True,
                )
                ticket_count += 1
                print(
                    f"[_generate_crew_tickets_sync] Generated crew ticket for {member.first_name} {member.last_name}: {ticket.ticketId}"
                )
                
                # Enhanced logging for email tracking with validation
                validated_email, validated_first, validated_last, email_valid = _ensure_email_delivery(
                    member, member.email if member else None, 
                    member.first_name if member else None, 
                    member.last_name if member else None
                )
                
                if email_valid:
                    print(f"[_generate_crew_tickets_sync] ✅ Email validation passed for crew member: {validated_email}")
                    # Force email verification
                    _force_email_send_verification()
                else:
                    print(f"[_generate_crew_tickets_sync] ❌ Email validation FAILED for crew member: {member.first_name} {member.last_name}")
                    print(f"[_generate_crew_tickets_sync] ⚠️  TICKET GENERATED BUT NO EMAIL WILL BE SENT!")
                    
            except Exception as e:
                print(
                    f"[_generate_crew_tickets_sync] Error generating crew ticket for {member.first_name} {member.last_name}: {e}"
                )
                import traceback

                print(f"[_generate_crew_tickets_sync] Traceback:")
                traceback.print_exc()
    except Crew.DoesNotExist:
        print(f"[_generate_crew_tickets_sync] Crew with ID {crew_id} not found.")
    except Exception as e:
        print(
            f"[_generate_crew_tickets_sync] Unexpected error in crew ticket generation: {e}"
        )
        import traceback

        print(f"[_generate_crew_tickets_sync] Full traceback:")
        traceback.print_exc()

    print(
        f"[_generate_crew_tickets_sync] Crew ticket generation complete. Generated {ticket_count} tickets"
    )
    print(
        f"[_generate_crew_tickets_sync] ========== CREW TICKET GENERATION COMPLETE =========="
    )
    return ticket_count


def _generate_regular_tickets_sync(
    user, ticket_info, event, session_id, cart_key, session
):
    """Synchronous version of generating regular tickets"""
    print(
        f"[_generate_regular_tickets_sync] ========== STARTING REGULAR TICKET GENERATION =========="
    )
    print(f"[_generate_regular_tickets_sync] User: {user}")
    print(f"[_generate_regular_tickets_sync] Ticket info: {ticket_info}")
    print(f"[_generate_regular_tickets_sync] Event: {event.title} ({event.eventId})")
    print(f"[_generate_regular_tickets_sync] Session ID: {session_id}")
    print(f"[_generate_regular_tickets_sync] Cart key: {cart_key}")

    from eventTicketsApp.views import generateTicket

    ticket_count = 0
    try:
        # Get customer information
        print(f"[_generate_regular_tickets_sync] Getting customer information")
        first_name, last_name, email = _get_customer_info_sync(user, session)
        print(
            f"[_generate_regular_tickets_sync] Customer info - Name: {first_name} {last_name}, Email: {email}"
        )
        
        # Ensure we have an email address - this is critical for ticket delivery
        if not email and user:
            email = user.email
            print(f"[_generate_regular_tickets_sync] Using user email as fallback: {email}")
        
        if not email:
            print(f"[_generate_regular_tickets_sync] ⚠️  CRITICAL: No email address available for ticket delivery!")
            print(f"[_generate_regular_tickets_sync] User: {user}")
            print(f"[_generate_regular_tickets_sync] Session customer_details: {getattr(session, 'customer_details', 'None')}")
            # Still generate ticket but log the issue
        else:
            print(f"[_generate_regular_tickets_sync] ✅ Email confirmed for ticket delivery: {email}")

        # Generate tickets
        quantity = int(ticket_info.get("quantity", 1))
        print(
            f"[_generate_regular_tickets_sync] Generating {quantity} tickets for {first_name} {last_name}"
        )

        for i in range(quantity):
            print(
                f"[_generate_regular_tickets_sync] Generating ticket {i+1}/{quantity}"
            )
            try:
                # Create a comprehensive mock request object for email functionality
                from django.http import HttpRequest
                from django.contrib.auth.models import AnonymousUser
                mock_request = HttpRequest()
                mock_request.META['HTTP_HOST'] = 'waveoncampus.com'
                mock_request.META['wsgi.url_scheme'] = 'https'
                mock_request.META['SERVER_NAME'] = 'waveoncampus.com'
                mock_request.META['SERVER_PORT'] = '443'
                mock_request.is_secure = lambda: True
                mock_request.user = user if user else AnonymousUser()
                mock_request.method = 'POST'
                
                # Validate email before ticket generation
                validated_email, validated_first, validated_last, email_valid = _ensure_email_delivery(
                    user, email, first_name, last_name
                )
                
                ticket = generateTicket(
                    request=mock_request,
                    event=event,
                    user=user if user else None,
                    guestFirstName=validated_first,
                    guestLastName=validated_last,
                    guestEmail=validated_email,
                    stripe_session_id=session_id,
                    from_api=True,
                )
                print(
                    f"[_generate_regular_tickets_sync] Ticket {i+1} generated: {ticket.ticketId}"
                )
                ticket_count += 1
                
                # Enhanced logging for email tracking with validation
                validated_email, validated_first, validated_last, email_valid = _ensure_email_delivery(
                    user, email, first_name, last_name
                )
                
                if email_valid:
                    print(f"[_generate_regular_tickets_sync] ✅ Email validation passed: {validated_email}")
                    # Force email verification for first ticket only
                    if i == 0:
                        _force_email_send_verification()
                else:
                    print(f"[_generate_regular_tickets_sync] ❌ Email validation FAILED for ticket generation")
                    print(f"[_generate_regular_tickets_sync] ⚠️  TICKET GENERATED BUT NO EMAIL WILL BE SENT!")

                # Update the ticket_sold count in the PaidFreeTicket model only once per cart item
                if i == 0:  # Only update on first ticket to avoid duplicate updates
                    print(
                        f"[_generate_regular_tickets_sync] Updating ticket sold count for cart key: {cart_key}"
                    )
                    _update_ticket_sold_count_sync(cart_key, event)
            except Exception as e:
                print(
                    f"[_generate_regular_tickets_sync] Error generating individual ticket {i+1}: {e}"
                )
                import traceback

                print(f"[_generate_regular_tickets_sync] Traceback for ticket {i+1}:")
                traceback.print_exc()

    except Exception as e:
        print(f"[_generate_regular_tickets_sync] Error generating regular tickets: {e}")
        import traceback

        print(f"[_generate_regular_tickets_sync] Full traceback:")
        traceback.print_exc()

    print(
        f"[_generate_regular_tickets_sync] Regular ticket generation complete. Generated {ticket_count} tickets"
    )
    print(
        f"[_generate_regular_tickets_sync] ========== REGULAR TICKET GENERATION COMPLETE =========="
    )
    return ticket_count


def _get_customer_info_sync(user, session):
    """Synchronous version of getting customer information from user or Stripe session"""
    print(f"[_get_customer_info_sync] ========== GETTING CUSTOMER INFO ==========")
    print(f"[_get_customer_info_sync] User: {user}")
    print(f"[_get_customer_info_sync] Session: {session}")

    if user:
        print(f"[_get_customer_info_sync] Using authenticated user information")
        first_name = user.first_name
        last_name = user.last_name
        email = user.email
        print(
            f"[_get_customer_info_sync] User info - Name: {first_name} {last_name}, Email: {email}"
        )
    else:
        print(
            f"[_get_customer_info_sync] No user provided, extracting from Stripe session"
        )
        # Get customer details from Stripe session
        first_name, last_name, email = "", "", ""

        print(f"[_get_customer_info_sync] Checking session customer_details")
        if hasattr(session, "customer_details") and session.customer_details:
            print(
                f"[_get_customer_info_sync] Customer details found: {session.customer_details}"
            )

            # Split the name on whitespace
            if (
                hasattr(session.customer_details, "name")
                and session.customer_details.name
            ):
                print(
                    f"[_get_customer_info_sync] Customer name found: {session.customer_details.name}"
                )
                name_parts = session.customer_details.name.split()
                first_name = name_parts[0] if name_parts else ""
                last_name = name_parts[-1] if len(name_parts) > 1 else ""
                print(
                    f"[_get_customer_info_sync] Name parts: {name_parts}, First: {first_name}, Last: {last_name}"
                )
            else:
                print(f"[_get_customer_info_sync] No customer name found in session")

            if (
                hasattr(session.customer_details, "email")
                and session.customer_details.email
            ):
                email = session.customer_details.email
                print(f"[_get_customer_info_sync] Customer email found: {email}")
            else:
                print(f"[_get_customer_info_sync] No customer email found in session")
        else:
            print(f"[_get_customer_info_sync] No customer_details found in session")
            
        # If we still don't have customer info, try to get it from the Stripe customer object
        if not email and hasattr(session, 'customer') and session.customer:
            print(f"[_get_customer_info_sync] Trying to get email from Stripe customer: {session.customer}")
            try:
                import stripe
                customer = stripe.Customer.retrieve(session.customer)
                if customer.email:
                    email = customer.email
                    print(f"[_get_customer_info_sync] Found email from Stripe customer: {email}")
                if customer.name and not first_name:
                    name_parts = customer.name.split()
                    first_name = name_parts[0] if name_parts else ""
                    last_name = name_parts[-1] if len(name_parts) > 1 else ""
                    print(f"[_get_customer_info_sync] Found name from Stripe customer: {first_name} {last_name}")
            except Exception as e:
                print(f"[_get_customer_info_sync] Error retrieving Stripe customer: {e}")
                
        # Last resort: try to get email from payment intent metadata
        if not email and hasattr(session, 'payment_intent') and session.payment_intent:
            print(f"[_get_customer_info_sync] Trying to get email from payment intent metadata")
            try:
                import stripe
                payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent)
                if payment_intent.receipt_email:
                    email = payment_intent.receipt_email
                    print(f"[_get_customer_info_sync] Found receipt email: {email}")
            except Exception as e:
                print(f"[_get_customer_info_sync] Error retrieving payment intent: {e}")

    print(
        f"[_get_customer_info_sync] Final customer info - Name: {first_name} {last_name}, Email: {email}"
    )
    print(f"[_get_customer_info_sync] ========== CUSTOMER INFO COMPLETE ==========")
    return first_name, last_name, email


def _update_ticket_sold_count_sync(cart_key, event):
    """Synchronous version of updating the ticket_sold count in the PaidFreeTicket model"""
    print(
        f"[_update_ticket_sold_count_sync] ========== UPDATING TICKET SOLD COUNT =========="
    )
    print(f"[_update_ticket_sold_count_sync] Cart key: {cart_key}")
    print(f"[_update_ticket_sold_count_sync] Event: {event.title} ({event.eventId})")

    try:
        # Find the ticket type and increment its sold count
        # Try by ticket_id first, then by name match
        print(
            f"[_update_ticket_sold_count_sync] Trying to find PaidFreeTicket by ticket_id: {cart_key}"
        )
        ticket_type = None

        try:
            import uuid

            # Check if cart_key is a valid UUID
            uuid.UUID(cart_key)
            # If valid UUID, try to find by ticket_id
            ticket_type = PaidFreeTicket.objects.get(ticket_id=cart_key, event=event)
            print(
                f"[_update_ticket_sold_count_sync] Found ticket by ticket_id: {ticket_type.ticket_name}"
            )
        except (ValueError, PaidFreeTicket.DoesNotExist):
            print(
                f"[_update_ticket_sold_count_sync] Not found by ticket_id or invalid UUID, trying by name matching"
            )
            # If not a valid UUID or not found, try to find by searching all tickets
            # This is a fallback for cart keys that don't match database IDs
            available_tickets = PaidFreeTicket.objects.filter(event=event)
            print(
                f"[_update_ticket_sold_count_sync] Available ticket types for this event:"
            )
            for ticket in available_tickets:
                print(
                    f"[_update_ticket_sold_count_sync]   - {ticket.ticket_name} (ID: {ticket.ticket_id}, PK: {ticket.pk})"
                )

            # If there's only one ticket type, use it
            if available_tickets.count() == 1:
                ticket_type = available_tickets.first()
                print(
                    f"[_update_ticket_sold_count_sync] Using single available ticket: {ticket_type.ticket_name}"
                )
            else:
                print(
                    f"[_update_ticket_sold_count_sync] Multiple ticket types found, cannot determine which one to update"
                )

        if ticket_type:
            print(
                f"[_update_ticket_sold_count_sync] Current ticket_sold: {ticket_type.ticket_sold}"
            )
            ticket_type.ticket_sold += 1
            ticket_type.save()
            print(
                f"[_update_ticket_sold_count_sync] Updated ticket_sold count for {ticket_type.ticket_name}: now {ticket_type.ticket_sold}"
            )
            print(
                f"[_update_ticket_sold_count_sync] ========== TICKET SOLD COUNT UPDATE COMPLETE =========="
            )
        else:
            print(
                f"[_update_ticket_sold_count_sync] Could not find ticket type with cart_key {cart_key} for event {event.eventId}"
            )
            print(
                f"[_update_ticket_sold_count_sync] ========== TICKET SOLD COUNT UPDATE FAILED =========="
            )

    except Exception as e:
        print(f"[_update_ticket_sold_count_sync] Error updating ticket_sold count: {e}")
        import traceback

        print(f"[_update_ticket_sold_count_sync] Full traceback:")
        traceback.print_exc()
        print(
            f"[_update_ticket_sold_count_sync] ========== TICKET SOLD COUNT UPDATE ERROR =========="
        )


def _generate_tickets_from_stripe_session_sync(user_id, session_id, session):
    """Fallback method to generate tickets directly from Stripe session when cart reconstruction fails"""
    print(
        f"[_generate_tickets_from_stripe_session_sync] ========== STARTING FALLBACK TICKET GENERATION =========="
    )
    print(f"[_generate_tickets_from_stripe_session_sync] User ID: {user_id}")
    print(f"[_generate_tickets_from_stripe_session_sync] Session ID: {session_id}")
    print(f"[_generate_tickets_from_stripe_session_sync] Session: {session}")

    from eventTicketsApp.views import generateTicket

    ticket_count = 0

    try:
        # Get line items from the session
        print(
            f"[_generate_tickets_from_stripe_session_sync] Getting line items from session"
        )
        line_items = stripe.checkout.Session.list_line_items(session_id)
        print(
            f"[_generate_tickets_from_stripe_session_sync] Found {len(line_items.data)} line items"
        )

        for i, item in enumerate(line_items.data):
            print(
                f"[_generate_tickets_from_stripe_session_sync] Line item {i}: {item.description}, quantity: {item.quantity}"
            )

        # Get user if authenticated
        user = None
        if user_id:
            print(
                f"[_generate_tickets_from_stripe_session_sync] Looking up user with ID: {user_id}"
            )
            try:
                user = CustomUser.objects.get(id=user_id)
                print(
                    f"[_generate_tickets_from_stripe_session_sync] User found: {user.username}"
                )
            except CustomUser.DoesNotExist:
                print(
                    f"[_generate_tickets_from_stripe_session_sync] User with ID {user_id} not found"
                )
        else:
            print(
                f"[_generate_tickets_from_stripe_session_sync] No user ID provided (guest)"
            )

        # Get customer info from session
        print(f"[_generate_tickets_from_stripe_session_sync] Getting customer info")
        first_name, last_name, email = _get_customer_info_sync(user, session)
        print(
            f"[_generate_tickets_from_stripe_session_sync] Customer: {first_name} {last_name} ({email})"
        )

        # Get event from payment intent metadata
        event = None
        if session.payment_intent:
            print(
                f"[_generate_tickets_from_stripe_session_sync] Getting event from payment intent: {session.payment_intent}"
            )
            try:
                payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent)
                print(
                    f"[_generate_tickets_from_stripe_session_sync] Payment intent metadata: {payment_intent.metadata}"
                )
                event_id = payment_intent.metadata.get("event_id")
                print(
                    f"[_generate_tickets_from_stripe_session_sync] Event ID from metadata: {event_id}"
                )
                if event_id:
                    event = Event.objects.get(eventId=event_id)
                    print(
                        f"[_generate_tickets_from_stripe_session_sync] Event found: {event.title}"
                    )
            except Exception as e:
                print(
                    f"[_generate_tickets_from_stripe_session_sync] Error getting event from payment intent: {e}"
                )
                import traceback

                print(f"[_generate_tickets_from_stripe_session_sync] Traceback:")
                traceback.print_exc()
        else:
            print(
                f"[_generate_tickets_from_stripe_session_sync] No payment intent found in session"
            )

        if not event:
            print(
                f"[_generate_tickets_from_stripe_session_sync] Could not determine event for ticket generation"
            )
            return 0

        # Generate tickets based on line items (excluding service fees)
        print(
            f"[_generate_tickets_from_stripe_session_sync] Generating tickets from line items"
        )
        for i, item in enumerate(line_items.data):
            if "Service Fee" not in item.description:
                print(
                    f"[_generate_tickets_from_stripe_session_sync] Processing ticket line item {i}: {item.description}"
                )
                # Generate tickets for this line item
                quantity = item.quantity
                print(
                    f"[_generate_tickets_from_stripe_session_sync] Generating {quantity} tickets for this line item"
                )

                for j in range(quantity):
                    print(
                        f"[_generate_tickets_from_stripe_session_sync] Generating ticket {j+1}/{quantity}"
                    )
                    try:
                        # Create a comprehensive mock request object for email functionality
                        from django.http import HttpRequest
                        from django.contrib.auth.models import AnonymousUser
                        mock_request = HttpRequest()
                        mock_request.META['HTTP_HOST'] = 'waveoncampus.com'
                        mock_request.META['wsgi.url_scheme'] = 'https'
                        mock_request.META['SERVER_NAME'] = 'waveoncampus.com'
                        mock_request.META['SERVER_PORT'] = '443'
                        mock_request.is_secure = lambda: True
                        mock_request.user = user if user else AnonymousUser()
                        mock_request.method = 'POST'
                        
                        # Validate email before ticket generation
                        validated_email, validated_first, validated_last, email_valid = _ensure_email_delivery(
                            user, email, first_name, last_name
                        )
                        
                        ticket = generateTicket(
                            request=mock_request,
                            event=event,
                            user=user if user else None,
                            guestFirstName=validated_first,
                            guestLastName=validated_last,
                            guestEmail=validated_email,
                            stripe_session_id=session_id,
                            from_api=True,
                        )
                        ticket_count += 1
                        print(
                            f"[_generate_tickets_from_stripe_session_sync] Ticket {j+1} generated: {ticket.ticketId}"
                        )
                        
                        # Enhanced logging for email tracking with validation
                        validated_email, validated_first, validated_last, email_valid = _ensure_email_delivery(
                            user, email, first_name, last_name
                        )
                        
                        if email_valid:
                            print(f"[_generate_tickets_from_stripe_session_sync] ✅ Email validation passed: {validated_email}")
                            # Force email verification for first ticket only
                            if j == 0:
                                _force_email_send_verification()
                        else:
                            print(f"[_generate_tickets_from_stripe_session_sync] ❌ Email validation FAILED for fallback ticket generation")
                            print(f"[_generate_tickets_from_stripe_session_sync] ⚠️  TICKET GENERATED BUT NO EMAIL WILL BE SENT!")
                            
                    except Exception as e:
                        print(
                            f"[_generate_tickets_from_stripe_session_sync] Error generating ticket {j+1}: {e}"
                        )
                        import traceback

                        print(
                            f"[_generate_tickets_from_stripe_session_sync] Ticket generation error traceback:"
                        )
                        traceback.print_exc()

                print(
                    f"[_generate_tickets_from_stripe_session_sync] Generated {quantity} tickets from fallback method for {item.description}"
                )
            else:
                print(
                    f"[_generate_tickets_from_stripe_session_sync] Skipping service fee item: {item.description}"
                )

        print(
            f"[_generate_tickets_from_stripe_session_sync] Fallback ticket generation completed. Total tickets: {ticket_count}"
        )
        print(
            f"[_generate_tickets_from_stripe_session_sync] ========== FALLBACK TICKET GENERATION COMPLETE =========="
        )
        return ticket_count

    except Exception as e:
        print(
            f"[_generate_tickets_from_stripe_session_sync] Error in fallback ticket generation: {e}"
        )
        import traceback

        print(f"[_generate_tickets_from_stripe_session_sync] Full traceback:")
        traceback.print_exc()
        print(
            f"[_generate_tickets_from_stripe_session_sync] ========== FALLBACK TICKET GENERATION ERROR =========="
        )
        return 0


def _validate_email_configuration():
    """Helper function to validate Django email configuration"""
    from django.conf import settings
    
    print(f"[Email Config] ========== EMAIL CONFIGURATION VALIDATION ==========")
    
    # Check basic email settings
    email_backend = getattr(settings, 'EMAIL_BACKEND', 'Not set')
    email_host = getattr(settings, 'EMAIL_HOST', 'Not set')
    email_port = getattr(settings, 'EMAIL_PORT', 'Not set')
    email_use_tls = getattr(settings, 'EMAIL_USE_TLS', 'Not set')
    email_use_ssl = getattr(settings, 'EMAIL_USE_SSL', 'Not set')
    default_from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not set')
    
    print(f"[Email Config] EMAIL_BACKEND: {email_backend}")
    print(f"[Email Config] EMAIL_HOST: {email_host}")
    print(f"[Email Config] EMAIL_PORT: {email_port}")
    print(f"[Email Config] EMAIL_USE_TLS: {email_use_tls}")
    print(f"[Email Config] EMAIL_USE_SSL: {email_use_ssl}")
    print(f"[Email Config] DEFAULT_FROM_EMAIL: {default_from_email}")
    
    # Check if basic configuration is present
    config_issues = []
    if email_backend == 'Not set':
        config_issues.append("EMAIL_BACKEND not configured")
    if email_host == 'Not set':
        config_issues.append("EMAIL_HOST not configured")
    if default_from_email == 'Not set':
        config_issues.append("DEFAULT_FROM_EMAIL not configured")
    
    if config_issues:
        print(f"[Email Config] ⚠️  Configuration Issues Found:")
        for issue in config_issues:
            print(f"[Email Config]   - {issue}")
    else:
        print(f"[Email Config] ✅ Basic email configuration appears to be set")
    
    print(f"[Email Config] ========== EMAIL CONFIGURATION VALIDATION COMPLETE ==========")
    return len(config_issues) == 0


def _test_email_functionality():
    """Helper function to test if email functionality is working"""
    from django.core.mail import send_mail
    from django.conf import settings
    
    print(f"[Email Test] ========== EMAIL FUNCTIONALITY TEST ==========")
    
    try:
        # Try to send a test email (but don't actually send it)
        from django.core.mail import get_connection
        
        connection = get_connection()
        print(f"[Email Test] ✅ Email connection established successfully")
        print(f"[Email Test] Connection type: {type(connection)}")
        return True
        
    except Exception as e:
        print(f"[Email Test] ❌ Email connection failed: {e}")
        import traceback
        print(f"[Email Test] Traceback:")
        traceback.print_exc()
        return False
    
    finally:
        print(f"[Email Test] ========== EMAIL FUNCTIONALITY TEST COMPLETE ==========")


# Call email validation when the module is loaded
try:
    _validate_email_configuration()
    _test_email_functionality()
except Exception as e:
    print(f"[Email Init] Error during email configuration validation: {e}")


def _ensure_email_delivery(user, email, first_name, last_name):
    """
    Comprehensive function to ensure we have all necessary information for email delivery
    Returns: (final_email, final_first_name, final_last_name, validation_passed)
    """
    print(f"[_ensure_email_delivery] ========== EMAIL DELIVERY VALIDATION ==========")
    print(f"[_ensure_email_delivery] Input - User: {user}, Email: {email}, Name: {first_name} {last_name}")
    
    final_email = email
    final_first_name = first_name
    final_last_name = last_name
    validation_passed = True
    
    # Priority 1: Use provided email if valid
    if final_email and "@" in final_email:
        print(f"[_ensure_email_delivery] ✅ Valid email provided: {final_email}")
    # Priority 2: Use user email if authenticated
    elif user and hasattr(user, 'email') and user.email:
        final_email = user.email
        print(f"[_ensure_email_delivery] ✅ Using authenticated user email: {final_email}")
    else:
        print(f"[_ensure_email_delivery] ❌ NO VALID EMAIL FOUND!")
        validation_passed = False
    
    # Ensure we have names
    if not final_first_name and user and hasattr(user, 'first_name'):
        final_first_name = user.first_name
        print(f"[_ensure_email_delivery] Using user first name: {final_first_name}")
    
    if not final_last_name and user and hasattr(user, 'last_name'):
        final_last_name = user.last_name
        print(f"[_ensure_email_delivery] Using user last name: {final_last_name}")
    
    # Final validation
    if not final_email or "@" not in final_email:
        print(f"[_ensure_email_delivery] ❌ CRITICAL: Invalid or missing email address: {final_email}")
        validation_passed = False
    else:
        print(f"[_ensure_email_delivery] ✅ Email validation passed: {final_email}")
    
    print(f"[_ensure_email_delivery] Final result - Email: {final_email}, Name: {final_first_name} {final_last_name}, Valid: {validation_passed}")
    print(f"[_ensure_email_delivery] ========== EMAIL DELIVERY VALIDATION COMPLETE ==========")
    
    return final_email, final_first_name, final_last_name, validation_passed


def _force_email_send_verification():
    """Force verification that email sending is working properly"""
    print(f"[_force_email_send_verification] ========== FORCING EMAIL VERIFICATION ==========")
    
    try:
        from django.core.mail import get_connection
        from django.conf import settings
        
        # Test email connection
        connection = get_connection()
        print(f"[_force_email_send_verification] ✅ Email connection established")
        
        # Validate settings
        email_backend = getattr(settings, 'EMAIL_BACKEND', None)
        email_host = getattr(settings, 'EMAIL_HOST', None)
        default_from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        
        print(f"[_force_email_send_verification] Email Backend: {email_backend}")
        print(f"[_force_email_send_verification] Email Host: {email_host}")
        print(f"[_force_email_send_verification] Default From Email: {default_from_email}")
        
        if not email_backend:
            print(f"[_force_email_send_verification] ❌ EMAIL_BACKEND not configured!")
            return False
            
        if not default_from_email:
            print(f"[_force_email_send_verification] ❌ DEFAULT_FROM_EMAIL not configured!")
            return False
            
        print(f"[_force_email_send_verification] ✅ Email configuration appears valid")
        return True
        
    except Exception as e:
        print(f"[_force_email_send_verification] ❌ Email verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print(f"[_force_email_send_verification] ========== EMAIL VERIFICATION COMPLETE ==========")


# Pydantic models for ticket details API
class TicketDetailsResponse(BaseModel):
    """Pydantic model for detailed ticket response"""
    
    ticket_id: str
    main_id: str
    status: str
    created_at: str
    updated_at: str
    
    # Event information
    event: Dict[str, Any]
    
    # User information (if authenticated user)
    user_info: Optional[Dict[str, Any]] = None
    
    # Guest information (if guest ticket)
    guest_info: Optional[Dict[str, Any]] = None
    
    # QR Code information
    qr_code_data: Optional[str] = None
    qr_code_image_url: Optional[str] = None
    
    # Ticket URLs
    activation_link: str
    view_link: str
    
    # Purchase information
    stripe_session_id: Optional[str] = None
    is_crew_ticket: bool = False
    
    # Additional metadata
    metadata: Dict[str, Any]


@router.get(
    "/{ticketId}/details",
    response_model=TicketDetailsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_ticket_details(
    ticketId: str,
    request: Request,
    current_user: Optional[CustomUser] = Depends(get_current_user_object),
):
    """
    Get comprehensive details for a specific ticket by ticket ID.
    
    This endpoint returns all available information about a ticket including
    event details, user/guest information, QR code data, and ticket status.
    
    Args:
        ticketId: The UUID of the ticket to retrieve
        request: The FastAPI request object
        current_user: Optional authenticated user
        
    Returns:
        TicketDetailsResponse: Comprehensive ticket information
        
    Raises:
        HTTPException: For various validation and access errors
    """
    print(f"[get_ticket_details API] Function called with ticketId: {ticketId}")
    print(f"[get_ticket_details API] Current user: {current_user.id if current_user else 'None'}")
    
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]
    
    # Get comprehensive request information for enhanced logging
    request_info = get_comprehensive_request_info(request)
    
    print(create_enhanced_log_message("get_ticket_details API", "========== TICKET DETAILS REQUEST START ==========", request_info))
    print(create_enhanced_log_message("get_ticket_details API", f"Ticket ID: {ticketId}", request_info))
    print(create_enhanced_log_message("get_ticket_details API", f"User ID: {current_user.id if current_user else 'Guest'}", request_info))
    
    if not ticketId:
        print(create_enhanced_log_message("get_ticket_details API", "ERROR: Ticket ID is required", request_info))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ticket ID is required"
        )
    
    @database_sync_to_async
    def get_ticket_comprehensive_details(ticket_id):
        """Get comprehensive ticket details from database"""
        print(f"[get_ticket_comprehensive_details] ========== RETRIEVING TICKET DETAILS ==========")
        print(f"[get_ticket_comprehensive_details] Searching for ticket ID: {ticket_id}")
        
        try:
            # Get the ticket
            ticket = Ticket.objects.select_related('event', 'user').get(mainId=ticket_id)
            print(f"[get_ticket_comprehensive_details] Ticket found: {ticket.ticketId}")
            print(f"[get_ticket_comprehensive_details] Ticket status: {ticket.status}")
            print(f"[get_ticket_comprehensive_details] Event: {ticket.event.title}")
            
            # Get event details
            event = ticket.event
            event_data = {
                "event_id": str(event.eventId),
                "title": event.title,
                "description": event.description,
                "date": event.date.isoformat() if event.date else None,
                "start_time": event.start_time.strftime("%H:%M") if event.start_time else None,
                "end_time": event.end_time.strftime("%H:%M") if event.end_time else None,
                "ticketing": event.ticketing,
                "age_restriction": event.age_restriction,
                "location": {
                    "building_name": event.building_name,
                    "street": event.street,
                    "city": event.city,
                    "state": event.state,
                    "country": event.country,
                    "zip_code": event.zip_code,
                    "hide_address": event.hide_address,
                },
                "host": {
                    "id": event.host.id,
                    "username": event.host.username,
                    "first_name": event.host.first_name,
                    "last_name": event.host.last_name,
                } if event.host else None,
                "event_type": event.event_type,
                "header_photo_url": event.header_photo.url if event.header_photo else None,
            }
            
            # Get user information if ticket belongs to authenticated user
            user_info = None
            if ticket.user:
                user_info = {
                    "user_id": ticket.user.id,
                    "username": ticket.user.username,
                    "first_name": ticket.user.first_name,
                    "last_name": ticket.user.last_name,
                    "email": ticket.user.email,
                    "date_joined": ticket.user.date_joined.isoformat(),
                }
                print(f"[get_ticket_comprehensive_details] User info included for: {ticket.user.username}")
            
            # Get guest information if it's a guest ticket
            guest_info = None
            if ticket.guestFirstName or ticket.guestLastName or ticket.guestEmail:
                guest_info = {
                    "first_name": ticket.guestFirstName,
                    "last_name": ticket.guestLastName,
                    "email": ticket.guestEmail,
                }
                print(f"[get_ticket_comprehensive_details] Guest info included for: {ticket.guestFirstName} {ticket.guestLastName}")
            
            # Generate ticket URLs
            from django.urls import reverse
            import os
            
            base_url = str(os.getenv("WEBSITE_DOMAIN", "https://waveoncampus.com"))
            activation_link = base_url + reverse("eventTickets:activateTicket", kwargs={"mainId": ticket.mainId})
            view_link = base_url + reverse("eventTickets:viewTicket", kwargs={"mainId": ticket.mainId})
            
            print(f"[get_ticket_comprehensive_details] Generated URLs - Activation: {activation_link}, View: {view_link}")
            
            # Get QR code information
            qr_code_image_url = None
            if ticket.qrCodeImage:
                try:
                    qr_code_image_url = ticket.qrCodeImage.url
                    print(f"[get_ticket_comprehensive_details] QR code image URL: {qr_code_image_url}")
                except Exception as e:
                    print(f"[get_ticket_comprehensive_details] Error getting QR code URL: {e}")
            
            # Determine if it's a crew ticket
            is_crew_ticket = bool(ticket.user and ticket.guestEmail and ticket.user.email != ticket.guestEmail)
            
            # Build metadata
            metadata = {
                "ticket_generated_via_api": True,
                "has_qr_code": bool(ticket.qrCodeImage),
                "is_guest_ticket": bool(guest_info and not user_info),
                "is_authenticated_user_ticket": bool(user_info and not guest_info),
                "is_mixed_ticket": bool(user_info and guest_info),
                "event_ticketing_type": event.ticketing,
                "ticket_main_id": ticket.mainId,
            }
            
            # Build the response
            ticket_details = {
                "ticket_id": str(ticket.ticketId),
                "main_id": ticket.mainId,
                "status": ticket.status,
                "created_at": ticket.created_at.isoformat(),
                "updated_at": ticket.updated_at.isoformat(),
                "event": event_data,
                "user_info": user_info,
                "guest_info": guest_info,
                "qr_code_data": ticket.qrCodeData,
                "qr_code_image_url": qr_code_image_url,
                "activation_link": activation_link,
                "view_link": view_link,
                "stripe_session_id": ticket.stripe_session_id,
                "is_crew_ticket": is_crew_ticket,
                "metadata": metadata,
            }
            
            print(f"[get_ticket_comprehensive_details] Ticket details compiled successfully")
            print(f"[get_ticket_comprehensive_details] ========== TICKET DETAILS RETRIEVAL COMPLETE ==========")
            
            return ticket_details
            
        except Ticket.DoesNotExist:
            print(f"[get_ticket_comprehensive_details] ERROR: Ticket not found with ID: {ticket_id}")
            return {"error": "Ticket not found"}
        except Exception as e:
            print(f"[get_ticket_comprehensive_details] ERROR: Unexpected error retrieving ticket: {e}")
            import traceback
            print(f"[get_ticket_comprehensive_details] Full traceback:")
            traceback.print_exc()
            return {"error": str(e)}
    
    try:
        print(create_enhanced_log_message("get_ticket_details API", "Calling database function to retrieve ticket details", request_info))
        result = await get_ticket_comprehensive_details(ticketId)
        
        if "error" in result:
            error_message = result["error"]
            print(create_enhanced_log_message("get_ticket_details API", f"Error retrieving ticket: {error_message}", request_info))
            
            if error_message == "Ticket not found":
                status_code = status.HTTP_404_NOT_FOUND
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                
            await notify_by_bot(
                f"**[API: get_ticket_details]** \n\n Error retrieving ticket details: {error_message} \n\n Ticket ID: {ticketId} \n\n User ID: {current_user.id if current_user else 'None'}",
                "API",
                "ERROR",
                device_info,
            )
            
            raise HTTPException(status_code=status_code, detail=error_message)
        
        print(create_enhanced_log_message("get_ticket_details API", f"Successfully retrieved ticket details for: {ticketId}", request_info))
        print(create_enhanced_log_message("get_ticket_details API", f"Ticket status: {result.get('status')}", request_info))
        print(create_enhanced_log_message("get_ticket_details API", f"Event: {result.get('event', {}).get('title', 'Unknown')}", request_info))
        print(create_enhanced_log_message("get_ticket_details API", "========== TICKET DETAILS REQUEST END ==========", request_info))
        
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(create_enhanced_log_message("get_ticket_details API", f"Unexpected error: {str(e)}", request_info))
        import traceback
        print(create_enhanced_log_message("get_ticket_details API", "Full traceback:", request_info))
        traceback.print_exc()
        
        await notify_by_bot(
            f"**[API: get_ticket_details]** \n\n Unexpected error: {str(e)} \n\n Ticket ID: {ticketId} \n\n User ID: {current_user.id if current_user else 'None'}",
            "API",
            "ERROR",
            device_info,
        )
        
        print(create_enhanced_log_message("get_ticket_details API", "========== TICKET DETAILS REQUEST ERROR END ==========", request_info))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving ticket details"
        )
