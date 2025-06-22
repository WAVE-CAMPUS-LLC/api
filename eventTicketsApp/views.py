from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
import uuid
from django.contrib import messages
from io import BytesIO
from decimal import Decimal
from django.core.files import File
import json
import os
from dotenv import load_dotenv
import time
from qr_code.qrcode import maker
from qr_code.qrcode.utils import QRCodeOptions
import stripe
from stripeManagementApp.customerSetup import CustomerAccount
from rest_framework.response import Response
from django.template.exceptions import TemplateDoesNotExist

from socialApp.models import Crew
from .models import PaidFreeTicket, Ticket, UserPayment, StripePlatformSettings
from eventManagementApp.models import CouponCode, Event, HostProfile
from authenticationApp.models import CustomUser


def initialize_stripe_settings():
    """Initialize default Stripe platform settings if they don't exist"""
    if not StripePlatformSettings.objects.exists():
        StripePlatformSettings.objects.create(
            salesTaxPercentage=Decimal("7.00"),  # 8% sales tax
            salesFeeAmount=Decimal("0.99"),  # $2 fee per ticket
            percentageStayingOnPlatform=Decimal("50.0"),  # 2.9% platform fee
        )


stripe.api_key = settings.STRIPE_SECRET_KEY

def paymentRedirect(request):
    return render(request, "eventTicketsApp/checkoutSession/paymentRedirect.html")

def hostedCheckout(request):
    try:
        # Try to get the cart from the request body first
        if request.method == 'POST' and request.body:
            try:
                # Parse the JSON data from the request body
                cart_data = json.loads(request.body)
                # Store the cart in the session
                request.session["cart"] = cart_data
                print(f"Cart data received: {cart_data}")
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                return JsonResponse({"error": "Invalid JSON data"}, status=400)
        
        # Get the cart from the session
        cart = request.session.get("cart", {})
        print(f"Cart from session: {cart}")
        
        if not cart:
            return JsonResponse({"error": "Cart is empty"}, status=400)
        
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
            return JsonResponse({"error": "No valid tickets in cart"}, status=400)
        
        # Calculate the total amount for tickets in dollars and convert to cents
        try:
            total_amount = sum(
                float(item.get("price", 0)) * int(item.get("quantity", 0))
                for item in ticket_items.values()
            )
            amount_in_cents = int(total_amount * 100)
            print(f"Total amount: {total_amount}, Amount in cents: {amount_in_cents}")
            
            # Only reject zero-amount carts if there's no discount applied
            # If there's a 100% discount, we should allow the checkout to proceed
            if amount_in_cents <= 0 and not has_discount and discount_percentage < 100:
                return JsonResponse({"error": "Invalid amount"}, status=400)
        except Exception as e:
            print(f"Error calculating total amount: {e}")
            return JsonResponse({"error": f"Error calculating total: {str(e)}"}, status=400)

        # Save the cart in the session if needed
        cart_id = str(uuid.uuid4())
        request.session[f"cart_data_{cart_id}"] = cart
        
        # Calculate your service fee (for example, 7% of the ticket total plus 99 cents)
        # For 100% discounted tickets, still apply a minimum service fee
        original_amount = sum(
            float(item.get("originalPrice", item.get("price", 0))) * int(item.get("quantity", 0))
            for item in ticket_items.values()
        )
        original_amount_in_cents = int(original_amount * 100)

        if amount_in_cents <= 0 and has_discount and discount_percentage >= 100:
            # For 100% discounts, apply a minimal service fee based on the original price
            fee_amount = max(99, int(original_amount_in_cents * 0.07) + 99)
        else:
            fee_amount = int(amount_in_cents * 0.07) + 99
        
        # Retrieve an event from one of the cart items and get its host's connected account ID
        try:
            # Filter out non-ticket keys (like coupon_code and discount_percentage)
            ticket_keys = [k for k in cart.keys() if k != 'coupon_code' and k != 'discount_percentage']
            if not ticket_keys:
                return JsonResponse({"error": "No tickets in cart"}, status=400)
                
            ticket = cart[ticket_keys[0]]
            print(f"Selected ticket for event lookup: {ticket}")
            
            try:
                if not isinstance(ticket, dict):
                    raise TypeError("Expected dict for ticket_info")

                event_id = ticket.get("eventId") or event_id_from_cart
                # rest of your ticket generation logic here...

            except Exception as e:
                print(f"[paymentSuccessful] ❌ Error processing cart_key '{cart_key}': {str(e)}")
                print(f" - Value: {ticket}")
                import traceback
                traceback.print_exc()
                
            event = Event.objects.get(eventId=event_id)
            host = CustomUser.objects.get(id=event.host.id)
            
            if not hasattr(host, 'connectAccountID') or not host.connectAccountID:
                return JsonResponse({"error": "Host does not have a connected Stripe account"}, status=400)
        except Event.DoesNotExist:
            return JsonResponse({"error": "Event not found"}, status=404)
        except CustomUser.DoesNotExist:
            return JsonResponse({"error": "Host not found"}, status=404)
        except Exception as e:
            print(f"Error retrieving event or host: {e}")
            return JsonResponse({"error": f"Error retrieving event details: {str(e)}"}, status=400)
        
        # Check if there's a valid coupon code in the cart
        valid_coupon_code = False
        discount_percentage = 0

        # Initialize coupon_code_value to None before checking
        coupon_code_value = None
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
                coupon = CouponCode.objects.get(code=coupon_code_value, event=event)
                
                # Coupons no longer expire - all coupons are valid
                valid_coupon_code = True
                discount_percentage = coupon.discount_percentage
                print(f"Valid coupon applied: {coupon_code_value}, Discount: {discount_percentage}%")
            except CouponCode.DoesNotExist:
                # Coupon doesn't exist or doesn't belong to this event
                valid_coupon_code = False
                print(f"Coupon not found: {coupon_code_value}")

        # Build Stripe line items for each ticket
        line_items = []
        try:
            for key, ticket in cart.items():
                # Skip non-ticket items like coupon_code and discount_percentage
                if key == 'coupon_code' or key == 'discount_percentage' or not isinstance(ticket, dict) or 'price' not in ticket or 'quantity' not in ticket:
                    continue
                    
                ticket_price = Decimal(str(ticket["price"]))  # Convert to Decimal safely
                ticket_quantity = int(ticket["quantity"])
                
                # The price in the cart is already discounted if a coupon was applied
                # No need to apply the discount again
                unit_amount = int(ticket_price * 100)
                print(f"Using price for {ticket['name']}: {ticket_price}, Unit amount: {unit_amount}")
                
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
                    "quantity": ticket_quantity,
                })
        except Exception as e:
            print(f"Error building line items: {e}")
            return JsonResponse({"error": f"Error building line items: {str(e)}"}, status=400)
        
        # For 100% discounts, we need to ensure there's at least one non-zero item
        # (the service fee) to make Stripe checkout work
        if not (amount_in_cents <= 0 and has_discount and discount_percentage >= 100):
            # Regular service fee for non-100% discounted tickets
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Service Fee",
                        "metadata": {
                            "type": "service_fee"
                        }
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
                    success_url=request.build_absolute_uri(reverse("eventTickets:paymentSuccessful")) + "?session_id={CHECKOUT_SESSION_ID}",
                    cancel_url=request.build_absolute_uri(reverse("eventTickets:paymentFailed")),
                    metadata={
                        'cart_data': json.dumps(cart),  # Store the entire cart in metadata
                        'event_id': str(event.eventId),
                        'event_title': event.title,
                        'is_discounted': 'true',
                        'discount_percentage': str(discount_percentage)
                    }
                )
            else:
                checkout_session = stripe.checkout.Session.create(
                    customer=request.user.customer_id if request.user.is_authenticated else None,
                    payment_method_types=["card"],
                    line_items=line_items,
                    mode="payment",
                    payment_intent_data={
                        # This tells Stripe to transfer only the ticket amount to the host
                        # The service fee stays with the platform
                        "transfer_data": {
                            "destination": host.connectAccountID,
                            "amount": amount_in_cents,  # Only transfer the ticket amount, not the fee
                        },
                        # Add metadata to help with cart reconstruction
                        "metadata": {
                            'cart_data': json.dumps(cart),  # Store the entire cart in metadata
                            'event_id': str(event.eventId),
                            'event_title': event.title,
                            'discount_percentage': str(discount_percentage) if has_discount else '0',
                            'ticket_amount': str(amount_in_cents),
                            'fee_amount': str(fee_amount)
                        }
                    },
                    metadata={
                        'cart_data': json.dumps(cart),  # Store the entire cart in metadata
                        'event_id': str(event.eventId),
                        'event_title': event.title,
                        'discount_percentage': str(discount_percentage) if has_discount else '0'
                    },
                    success_url=request.build_absolute_uri(reverse("eventTickets:paymentSuccessful")) + "?session_id={CHECKOUT_SESSION_ID}",
                    cancel_url=request.build_absolute_uri(reverse("eventTickets:paymentFailed")),
                )
            
            print(f"Checkout session created: {checkout_session.id}")
            return JsonResponse({"sessionUrl": checkout_session.url})
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e}")
            return JsonResponse({"error": f"Stripe error: {str(e)}"}, status=400)
        except Exception as e:
            print(f"Error creating checkout session: {e}")
            return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        import traceback
        print(f"Unexpected error in hostedCheckout: {e}")
        print(traceback.format_exc())
        return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)


def paymentSuccessful(request):
    # Get the cart from the session or initialize an empty one
    cart = request.session.get("cart", {})
    print(f"Cart from session: {json.dumps(cart, indent=2)}")
    
    session_id = request.GET.get("session_id")
    from_mobile = request.GET.get("from_mobile")
    if not session_id or session_id == "{CHECKOUT_SESSION_ID}":
        print("Error: session_id is missing or invalid.")
        return HttpResponse("Error: session_id is missing or invalid.", status=400)
    
    # Check if tickets have already been generated for this session
    print(f"[paymentSuccessful] Checking for tickets tied to session_id: {session_id}")
    existing_tickets = Ticket.objects.filter(stripe_session_id=session_id)
    
    if existing_tickets.exists():
        ticket_count = existing_tickets.count()
        print(f"Found {ticket_count} existing tickets for session {session_id}. Preventing duplicate generation.")
        
        # Clean up session data
        _clear_session_data(request)
        
        if from_mobile:
            return JsonResponse({"status": "paymentSuccessful", "tickets_generated": ticket_count, "duplicate": True}, status=200)
            
        # Render success page with existing ticket count
        return render(request, "eventTicketsApp/checkoutSession/paymentSuccessful.html", {
            "tickets_generated": ticket_count,
            "duplicate": True
        })
    
    try:
        print(f"Retrieving Stripe session: {session_id}")
        session = stripe.checkout.Session.retrieve(session_id)
        
        # Check if cart is empty but we have a valid session
        if not cart or len(cart) == 0:
            print("Cart is empty or contains only coupon info. Attempting to reconstruct from Stripe session.")
            cart = _reconstruct_cart_from_stripe(session)
    except Exception as e:
        print(f"Stripe error: {e}")
        import traceback
        traceback.print_exc()
        return HttpResponse(f"Stripe error: {e}", status=400)
    
    # Check if we still have an empty cart
    if not cart or len(cart) == 0 or all(k in ['coupon_code', 'discount_percentage'] for k in cart.keys()):
        print("Warning: Cart is still empty after reconstruction attempt.")
    
    # Generate tickets from cart items
    ticket_count = _generate_tickets_from_cart(request, cart, session_id, session)
    
    # Clean up session data
    _clear_session_data(request)
    
    if from_mobile:
        return JsonResponse({"status": "paymentSuccessful", "tickets_generated": ticket_count}, status=200)

    # Render success page
    return render(request, "eventTicketsApp/checkoutSession/paymentSuccessful.html", {"tickets_generated": ticket_count})


def _clear_session_data(request):
    """Helper function to clear session data"""
    if "cart" in request.session:
        del request.session["cart"]
        print("Cart cleared from session")
    if "checkout_user_info" in request.session:
        del request.session["checkout_user_info"]
        print("Checkout user info cleared from session")


def _reconstruct_cart_from_stripe(session):
    """Reconstruct cart from Stripe session data"""
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
            cart = _extract_cart_from_line_items(line_items.data)
        
        # If cart is still empty, try session metadata
        if not cart or all(k in ['coupon_code', 'discount_percentage'] for k in cart.keys()):
            cart = _extract_cart_from_metadata(session, payment_intent, line_items)
            
        print(f"Final reconstructed cart: {json.dumps(cart, indent=2)}")
    except Exception as e:
        print(f"Error reconstructing cart from Stripe session: {e}")
        import traceback
        traceback.print_exc()
    
    return cart


def _extract_cart_from_line_items(line_items):
    """Extract cart data from Stripe line items"""
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
                        
                        # Try to find the original ticket
                        try:
                            ticket = PaidFreeTicket.objects.get(ticket_id=original_ticket_id, event=event)
                            
                            cart[original_ticket_id] = {
                                "name": ticket.ticket_name,
                                "price": float(ticket.ticket_price),
                                "quantity": item.quantity,
                                "eventId": str(event.eventId)
                            }
                            continue
                        except Exception as e:
                            print(f"Error finding ticket with ticket_id={original_ticket_id}: {e}")
                    except (Event.DoesNotExist, PaidFreeTicket.DoesNotExist) as e:
                        print(f"Could not find original ticket/event: {e}")
        except Exception as e:
            print(f"Error accessing product metadata: {e}")
    
    return cart


def _extract_cart_from_metadata(session, payment_intent, line_items):
    """Extract cart data from session or payment intent metadata"""
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


def _generate_tickets_from_cart(request, cart, session_id, session):
    """Generate tickets from cart items"""
    ticket_count = 0
    
    # Special handling for event_id if it's a direct key in the cart
    event_id_from_cart = cart.get('event_id')
    if event_id_from_cart and isinstance(event_id_from_cart, str):
        print(f"Found event_id directly in cart: {event_id_from_cart}")
    
    for cart_key, ticket_info in cart.items():
        # Skip non-ticket items
        if cart_key in ['coupon_code', 'discount_percentage', 'event_id', 'coupon_id']:
            continue
            
        # Check if ticket_info is a dictionary before trying to use .get()
        if not isinstance(ticket_info, dict):
            print(f"Warning: ticket_info for {cart_key} is not a dictionary: DEUBUGGY {type(ticket_info)}")
            continue
            
        # Get event_id from the ticket_info or use the one from the cart
        try:
            event_id = ticket_info.get("eventId") or event_id_from_cart
        except Exception as e:
            print(f"Error getting event ID: DEUBUGGY {e}")
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
            ticket_count += _generate_crew_tickets(request, ticket_info, event, session_id)
        else:
            # Handle regular tickets
            ticket_count += _generate_regular_tickets(request, ticket_info, event, session_id, cart_key, session)
    
    print(f"Total tickets generated: {ticket_count}")
    return ticket_count


def _generate_crew_tickets(request, ticket_info, event, session_id):
    """Generate tickets for crew members"""
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
                    request=request,
                    event=event,
                    user=member if member else None,
                    guestFirstName=member.first_name if member else None,
                    guestLastName=member.last_name if member else None,
                    guestEmail=member.email if member else None,
                    crewTicket=(member != request.user),
                    stripe_session_id=session_id,
                )
                ticket_count += 1
                print(f"Generated crew ticket for {member.first_name} {member.last_name}")
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    f"Generated ticket for {member.first_name} {member.last_name}",
                )
            except Exception as e:
                print(f"Error generating crew ticket: {e}")
                import traceback
                traceback.print_exc()
    except Crew.DoesNotExist:
        print(f"Crew with ID {crew_id} not found.")
    
    return ticket_count


def _generate_regular_tickets(request, ticket_info, event, session_id, cart_key, session):
    """Generate regular tickets"""
    ticket_count = 0
    try:
        # Get customer information
        first_name, last_name, email = _get_customer_info(request, session)
        
        # Generate tickets
        quantity = int(ticket_info.get("quantity", 1))
        print(f"Generating {quantity} tickets for {first_name} {last_name}")
        
        for i in range(quantity):
            ticket = generateTicket(
                request=request,
                event=event,
                user=request.user if request.user.is_authenticated else None,
                guestFirstName=first_name,
                guestLastName=last_name,
                guestEmail=email,
                stripe_session_id=session_id,
            )
            ticket_count += 1
            
            # Update the ticket_sold count in the PaidFreeTicket model
            _update_ticket_sold_count(cart_key, event)
    except Exception as e:
        print(f"Error generating regular ticket: {e}")
        import traceback
        traceback.print_exc()
    
    return ticket_count


def _get_customer_info(request, session):
    """Get customer information from request or Stripe session"""
    if request.user.is_authenticated:
        first_name = request.user.first_name
        last_name = request.user.last_name
        email = request.user.email
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


def _update_ticket_sold_count(cart_key, event):
    """Update the ticket_sold count in the PaidFreeTicket model"""
    try:
        # Find the ticket type and increment its sold count
        ticket_type = PaidFreeTicket.objects.get(ticket_id=cart_key, event=event)
        ticket_type.ticket_sold += 1
        ticket_type.save()
        print(f"Updated ticket_sold count for {ticket_type.ticket_name}: now {ticket_type.ticket_sold}")
    except PaidFreeTicket.DoesNotExist:
        print(f"Could not find ticket type with ID {cart_key}")
    except Exception as e:
        print(f"Error updating ticket_sold count: {e}")


def paymentFailed(request):
    from_mobile = request.GET.get("from_mobile")
    # if from_mobile:
    #     # Use JsonResponse for mobile requests instead of DRF Response
    #     return JsonResponse({"status": "paymentFailed"}, status=200)
    return render(request, "eventTicketsApp/checkoutSession/paymentFailed.html", {"fromMobile": True})


@csrf_exempt
def stripeWebhook(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET_TEST
    time.sleep(10)
    print("Webhook received")
    payload = request.body
    signature_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    if not signature_header:
        print("Signature header missing")
        return HttpResponse(status=400)
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, signature_header, endpoint_secret
        )
    except ValueError as e:
        return HttpResponse(status=400)

    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)
        
    return JsonResponse({"status": "success"}, status=200)
    
    

def updateCartView(request):
    # Used in ajax Event Ticket updating.
    if request.method == "POST":
        try:
            # Get the cart data from the request
            cart_data = json.loads(request.body)

            # Save the cart data to the session
            request.session["cart"] = cart_data
            return JsonResponse({"success": True})
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON data"}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    return JsonResponse({"success": False, "error": "Only POST method is allowed"}, status=400)


@require_http_methods(["POST"])
def applyCouponCode(request):
    """Apply a coupon code to the cart"""
    try:
        data = json.loads(request.body)
        coupon_code = data.get('coupon_code')
        event_id = data.get('event_id')
        
        if not coupon_code or not event_id:
            return JsonResponse(
                {"success": False, "message": "Coupon code and event ID are required"}
            , status=400)
            
        try:
            event = Event.objects.get(eventId=event_id)
            coupon = CouponCode.objects.get(code=coupon_code, event=event)
            
            # Removed expiry date validation - coupons no longer expire
            
            # Get the current cart
            cart = request.session.get("cart", {})
            
            # Add the coupon code to the cart
            cart['coupon_code'] = coupon_code
            
            # Save the updated cart back to the session
            request.session["cart"] = cart
            
            return JsonResponse(
                {"success": True, "message": "Coupon applied successfully", "discount_percentage": coupon.discount_percentage}
            )
            
        except Event.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Event not found"}
            , status=404)
        except CouponCode.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Invalid coupon code for this event"}
            , status=404)
            
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON format"}
        , status=400)
    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"An error occurred: {str(e)}"}
        , status=500)


def viewTicket(request, mainId):
    ticket = get_object_or_404(Ticket, mainId=mainId)
    event = ticket.event

    if ticket:
        return render(
            request,
            "eventTicketsApp/ticket/viewTicket.html",
            {"ticket": ticket, "event": event},
        )
    else:
        return redirect("core:explore")

def activateTicket(request, mainId):
    ticket = get_object_or_404(Ticket, mainId=mainId)
    event = ticket.event

    # check if post action is "activate"
    if request.method == "POST" and request.POST.get("eventAction") == "activate":
        if ticket.status == "Scanned":
            messages.error(request, "Ticket is already activated")
            return redirect("eventTickets:activateTicket", mainId=mainId)
        ticket.status = "Scanned"
        ticket.save()
        messages.success(request, "Ticket activated successfully")
        return redirect("eventTickets:activateTicket", mainId=mainId)
    return render(
        request,
        "eventTicketsApp/ticket/activateTicket.html",
        {"ticket": ticket, "event": event},
    )


def generateTicket(
    request,
    event,
    user=None,
    guestFirstName=None,
    guestLastName=None,
    guestEmail=None,
    crewTicket=False,
    stripe_session_id=None,
    from_api=False
): 
    ticket = Ticket(
        user=user if user and user.is_authenticated else None,
        event=event,
        guestFirstName=guestFirstName if guestFirstName else user.first_name if user else None,
        guestLastName=guestLastName if guestLastName else user.last_name if user else None,
        guestEmail=guestEmail if guestEmail else user.email if user else None,
        stripe_session_id=stripe_session_id,
    )
    ticket.save()
      # Get the ticket's main ID and build the activation URL.
    ticketMainId = ticket.mainId
    activationLink = (
        (str(os.getenv("WEBSITE_DOMAIN")) + reverse("eventTickets:activateTicket", kwargs={"mainId": ticketMainId}))
        if from_api else 
        request.build_absolute_uri(reverse("eventTickets:activateTicket", kwargs={"mainId": ticketMainId})) 
    )
    viewLink = (
        (str(os.getenv("WEBSITE_DOMAIN")) + reverse("eventTickets:viewTicket", kwargs={"mainId": ticketMainId}))
        if from_api else
        request.build_absolute_uri(reverse("eventTickets:viewTicket", kwargs={"mainId": ticketMainId}))
    )
    # Use JSON data for the QR code with comprehensive ticket information
    qr_data = json.dumps(
        {
            "ticketId": str(ticket.ticketId),
            "eventId": str(event.eventId),
            "status": ticket.status,
            "guestFirstName": guestFirstName if guestFirstName else None,
            "guestLastName": guestLastName if guestLastName else None,
            "guestEmail": guestEmail if guestEmail else None,
            "userFirstName": user.first_name if user else None,
            "userLastName": user.last_name if user else None,
            "userEmail": user.email if user else None,
            "activationLink": activationLink,
        }
    )

    qr_code_options = QRCodeOptions(
        size=200,
        border=4,
        error_correction="M",
        image_format="png",
        dark_color="#000000",
        light_color="#ffffff",
    )

    try:
        # Generate the QR code with the activation URL.
        qr_code_image = maker.make_qr_code_image(
            data=qr_data, qr_code_options=qr_code_options, force_text=True
        )

        image_io = BytesIO(qr_code_image)
        ticket.qrCodeImage.save(f"{ticket.ticketId}.png", File(image_io), save=True)

        ticket.save()

        # Prepare email
        if guestEmail or (user and user.email):
            try:
                # Get the buyer's name for the subject.
                buyer_name = "Someone"
                if not from_api:
                    if request.user and request.user.is_authenticated:
                        buyer_name = request.user.first_name or "Someone"
                else:
                    buyer_name = guestFirstName
                
                subject = (
                    f"{buyer_name} bought a ticket for you for {event.title}"
                    if crewTicket
                    else f"Your Ticket for {event.title}"
                )
                message = (
                    "This ticket was bought by a crew member for you!\nYour QR code is attached."
                    if crewTicket
                    else "Thank you for your purchase!\nYour QR code is attached."
                )
                
                # Ensure we have a valid recipient email.
                recipient_email = guestEmail if guestEmail else user.email if user else None
                if not recipient_email:
                    print("No recipient email available, cannot send ticket email")
                    return ticket
                    
                recipient_list = [recipient_email]
                
                print(f"Email settings: DEFAULT_FROM_EMAIL={settings.DEFAULT_FROM_EMAIL}, EMAIL_HOST={settings.EMAIL_HOST}")
                
                # Use inline HTML email template as the primary and only method
                profile_link = "https://www.waveoncampus.com/profile"
                qrCodeHtml = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Your Event Ticket</title>
                </head>
                <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f0fdfa;">
                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f0fdfa; padding: 40px 0;">
                        <tr>
                            <td align="center">
                                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; box-shadow: 0 10px 25px rgba(20, 184, 166, 0.15); overflow: hidden; max-width: 600px; border: 1px solid #5eead4;">
                                    <!-- Header Section -->
                                    <tr>
                                        <td style="background: linear-gradient(135deg, #0d9488 0%, #14b8a6 50%, #2dd4bf 100%); padding: 40px 30px; text-align: center;">
                                            <h1 style="color: #ffffff; margin: 0; font-size: 32px; font-weight: 800; text-shadow: 0 2px 4px rgba(0,0,0,0.3); letter-spacing: -0.5px;">
                                                🎟️ Your Ticket is Ready!
                                            </h1>
                                            <p style="color: #ccfbf1; margin: 15px 0 0 0; font-size: 18px; font-weight: 500;">
                                                Successfully purchased and confirmed
                                            </p>
                                        </td>
                                    </tr>
                                    
                                    <!-- Event Details Section -->
                                    <tr>
                                        <td style="padding: 40px 30px; text-align: center;">
                                            <div style="background: linear-gradient(135deg, #0891b2 0%, #0284c7 100%); color: white; padding: 25px; border-radius: 12px; margin-bottom: 35px; box-shadow: 0 4px 15px rgba(8, 145, 178, 0.3);">
                                                <h2 style="margin: 0; font-size: 26px; font-weight: 700; text-shadow: 0 1px 3px rgba(0,0,0,0.3); line-height: 1.3;">
                                                    {event.title}
                                                </h2>
                                            </div>
                                            
                                            <p style="color: #0f766e; font-size: 20px; line-height: 1.6; margin: 0 0 35px 0; font-weight: 600;">
                                                🎉 <strong>Congratulations!</strong> Your ticket has been confirmed and is ready to use.
                                            </p>
                                            
                                            <!-- QR Code Section -->
                                            <div style="background: linear-gradient(135deg, #f0fdfa 0%, #ccfbf1 100%); border: 3px solid #5eead4; border-radius: 16px; padding: 30px; margin: 30px 0; box-shadow: 0 4px 15px rgba(94, 234, 212, 0.2);">
                                                <h3 style="color: #0f766e; margin: 0 0 20px 0; font-size: 20px; font-weight: 700;">
                                                    📱 Your QR Code Ticket
                                                </h3>
                                                <p style="color: #134e4a; margin: 0 0 20px 0; font-size: 16px; line-height: 1.5;">
                                                    <strong>Scan this QR code at the event entrance</strong><br>
                                                    Save this email or screenshot the QR code below
                                                </p>
                                                <div style="background-color: #ffffff; padding: 20px; border-radius: 12px; display: inline-block; border: 2px solid #2dd4bf;">
                                                    <img src="cid:qr_code" alt="Ticket QR Code" style="width: 200px; height: 200px; display: block; margin: 0 auto;" />
                                                </div>
                                                <p style="color: #0f766e; margin: 15px 0 0 0; font-size: 14px; font-weight: 600;">
                                                    Ticket ID: {ticket.ticketId}
                                                </p>
                                            </div>
                                            
                                            <div style="background-color: #ecfeff; border: 3px solid #22d3ee; border-radius: 12px; padding: 25px; margin: 25px 0;">
                                                <p style="color: #0e7490; margin: 0; font-size: 16px; font-weight: 600;">
                                                    💡 <strong>Important:</strong> Present this QR code at the event entrance for quick and easy check-in.
                                                </p>
                                            </div>
                                        </td>
                                    </tr>
                                    
                                    <!-- CTA Button Section -->
                                    <tr>
                                        <td style="padding: 0 30px 40px 30px; text-align: center;">
                                            <a href="{profile_link}" style="display: inline-block; background: linear-gradient(135deg, #0d9488 0%, #14b8a6 50%, #2dd4bf 100%); color: #ffffff; text-decoration: none; padding: 18px 40px; border-radius: 12px; font-size: 18px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; box-shadow: 0 6px 20px rgba(20, 184, 166, 0.4); transition: all 0.3s ease; border: 2px solid transparent;">
                                                🎫 View All My Tickets
                                            </a>
                                            
                                            <p style="color: #0f766e; font-size: 16px; margin: 25px 0 0 0; line-height: 1.6; font-weight: 600;">
                                                Click the button above to go to your profile, then click <strong>"My Tickets"</strong> to see all your event tickets.
                                            </p>
                                            
                                            <div style="background-color: #fefce8; border: 2px solid #eab308; border-radius: 12px; padding: 20px; margin: 25px 0; text-align: left;">
                                                <p style="color: #a16207; margin: 0; font-size: 15px; font-weight: 600;">
                                                    📱 <strong>Alternative Access:</strong>
                                                </p>
                                                <p style="color: #a16207; margin: 8px 0 0 0; font-size: 14px; line-height: 1.5;">
                                                    Can't click the button? Go to <strong>waveoncampus.com/profile</strong> and click "My Tickets" to access all your event tickets.
                                                </p>
                                            </div>
                                        </td>
                                    </tr>
                                    
                                    <!-- Footer Section -->
                                    <tr>
                                        <td style="background: linear-gradient(135deg, #f0fdfa 0%, #ccfbf1 100%); padding: 35px 30px; text-align: center; border-top: 2px solid #5eead4;">
                                            <p style="color: #0f766e; font-size: 16px; margin: 0 0 15px 0; font-weight: 600;">
                                                Need help? Contact our support team
                                            </p>
                                            <p style="color: #134e4a; font-size: 13px; margin: 0; line-height: 1.5; opacity: 0.8;">
                                                This is an automated message. Please do not reply to this email.<br>
                                                Make sure to arrive at the event with your QR code ready to scan.
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                </body>
                </html>
                """
                print("Using inline HTML email template")
                
                from_email = settings.DEFAULT_FROM_EMAIL
                
                print(f"Sending ticket email to: {recipient_list} from {from_email}")
                
                # Create a file attachment with the QR code.
                qr_attachment = None
                if ticket.qrCodeImage:
                    try:
                        qr_attachment = ticket.qrCodeImage.path
                        print(f"QR code attachment path: {qr_attachment}")
                    except Exception as e:
                        print(f"Error getting QR code attachment: {e}")
                
                # Send the email with inline QR code image.
                try:
                    from django.core.mail import EmailMultiAlternatives
                    from email.mime.image import MIMEImage
                    
                    email = EmailMultiAlternatives(
                        subject=subject,
                        body=message,
                        from_email=from_email,
                        to=recipient_list
                    )
                    email.attach_alternative(qrCodeHtml, "text/html")
                    
                    # Attach QR code image inline for email display
                    if qr_attachment and os.path.exists(qr_attachment):
                        with open(qr_attachment, 'rb') as f:
                            qr_image_data = f.read()
                            # Create inline image attachment with cid:qr_code
                            qr_image = MIMEImage(qr_image_data)
                            qr_image.add_header('Content-ID', '<qr_code>')
                            qr_image.add_header('Content-Disposition', 'inline', filename=f"ticket-{ticket.ticketId}.png")
                            email.attach(qr_image)
                            print(f"QR code image attached inline with CID: qr_code")
                    
                    email.send(fail_silently=False)
                    print(f"Email sent successfully with inline QR code to {recipient_list}")
                    
                except Exception as e:
                    print(f"Error sending email with inline QR code: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Fallback: try basic send_mail without inline image
                    try:
                        send_mail(
                            subject,
                            message,
                            from_email,
                            recipient_list,
                            fail_silently=False,
                            html_message=qrCodeHtml,
                        )
                        print(f"Fallback email sent successfully to {recipient_list} (without inline QR code)")
                    except Exception as e2:
                        print(f"Fallback email sending also failed: {e2}")
                        traceback.print_exc()
                
                # Add event to the user's purchased events if authenticated.
                if not from_api:
                    if request.user and request.user.is_authenticated and hasattr(request.user, 'user_profile'):
                        try:
                            request.user.user_profile.purchased_events.add(event)
                            print(f"Added event {event.title} to user's purchased events")
                        except Exception as e:
                            print(f"Error adding event to user's purchased events: {e}")
                elif user and user.user_profile:
                    try:
                        user.user_profile.purchased_events.add(event)
                        print(f"Added event {event.title} to user's purchased events")
                    except Exception as e:
                        print(f"Error adding event to user's purchased events: {e}")
            
            except Exception as e:
                print(f"Error sending ticket email: {e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"Error generating QR code: {e}")
        import traceback
        traceback.print_exc()
    
    return ticket

def verifyTicket(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            print(request.body)
            try:
                ticketId = data.get("ticketId")                
                eventId = data.get("eventId")
                status = data.get("status")
            except Exception as e:
                print(f"Error parsing ticket data DEUBUGGY: {e}")
                return JsonResponse(
                    {
                        "valid": False,
                        "message": "Invalid ticket data",
                    },
                    status=400,
                )
            
            if not all([ticketId, eventId, status]):
                return JsonResponse(
                    {"valid": False, "message": "Invalid ticket data"}, status=400
                )

            try:
                ticket = Ticket.objects.get(ticketId=ticketId, event__eventId=eventId)
            except Ticket.DoesNotExist:
                return JsonResponse(
                    {
                        "valid": False,
                        "message": "Ticket not found.",
                    },
                    status=404,
                )

            if ticket.status == "Scanned":
                return JsonResponse(
                    {
                        "valid": False,
                        "message": "Ticket already scanned.",
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
                    },
                    status=400,
                )

            elif ticket.status == "Invalid":
                return JsonResponse(
                    {
                        "valid": False,
                        "message": "Ticket already scanned.",
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
                    },
                    status=400,
                )

            ticket.status = "Scanned"
            ticket.save()
            return JsonResponse(
                {
                    "valid": True,
                    "message": f"{ticket.guestFirstName} {ticket.guestLastName}: Valid",
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
            )

        except json.JSONDecodeError:
            return JsonResponse(
                {
                    "valid": False,
                    "message": "Invalid JSON format",
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
                },
                status=400,
            )
        except Exception as e:
            print(f"Error verifying ticket: {e}")
            return JsonResponse(
                {
                    "valid": False,
                    "message": f"An error occurred: {e}",
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
                },
                status=500,
            )

    return JsonResponse(
        {
            "valid": False,
            "message": "Invalid request method",
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
                "userFirstName": (ticket.user.first_name if ticket.user else None),
                "userLastName": (ticket.user.last_name if ticket.user else None),
                "status": (ticket.status),
            },
        },
        status=405,
    )
