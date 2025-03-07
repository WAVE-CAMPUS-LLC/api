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

from socialApp.models import Crew
from .models import PaidFreeTicket, Ticket, UserPayment, StripePlatformSettings
from eventManagementApp.models import Event, HostProfile
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
    cart = request.session.get("cart", {})
    if not cart:
        return JsonResponse({"error": "Cart is empty"}, status=400)
    
    # Calculate the total amount for tickets in dollars and convert to cents
    total_amount = sum(
        float(item.get("price", 0)) * int(item.get("quantity", 0))
        for item in cart.values()
    )
    amount_in_cents = int(total_amount * 100)
    if amount_in_cents <= 0:
        return JsonResponse({"error": "Invalid amount"}, status=400)

    # Save the cart in the session if needed
    cart_id = str(uuid.uuid4())
    request.session[f"cart_data_{cart_id}"] = cart
    
    # Calculate your service fee (for example, 7% of the ticket total plus 99 cents)
    fee_amount = int(amount_in_cents * 0.07) + 99

    # Build Stripe line items for each ticket
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
    
    # Append a separate line item for the service fee so the user sees it
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

    # Retrieve an event from one of the cart items and get its host's connected account ID
    ticket = next(iter(cart.values()))
    event = Event.objects.get(eventId=ticket.get("eventId"))
    host = CustomUser.objects.get(id=event.host.id)  # Assumes the host has a field "connectAccountID"

    try:
        checkout_session = stripe.checkout.Session.create(
            customer=request.user.customer_id if request.user.is_authenticated else None,
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            payment_intent_data={
                # This tells Stripe to deduct your service fee from the total
                "application_fee_amount": fee_amount,
                # The remaining funds are transferred to the host's connected account
                "transfer_data": {
                    "destination": host.connectAccountID,
                },
            },
            success_url=request.build_absolute_uri(
                reverse("eventTickets:paymentSuccessful")
            )
            + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.build_absolute_uri(reverse("eventTickets:paymentFailed")),
        )
        return JsonResponse({"sessionUrl": checkout_session.url})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def paymentSuccessful(request):
    # Retrieve the cart from the session
    cart = request.session.get("cart", {})

    # If you collected additional user info in the session
    user_info = request.session.get("checkout_user_info", {})

    session_id = request.GET.get("session_id")
    if not session_id or session_id == "{CHECKOUT_SESSION_ID}":
        # Handle error: session_id was not replaced
        return HttpResponse("Error: session_id is missing or invalid.", status=400)
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        # Process session details...
    except Exception as e:
        return HttpResponse(f"Stripe error: {e}", status=400)
    
    # Loop over each cart item to generate tickets
    for cart_key, ticket_info in cart.items():
        event_id = ticket_info.get("eventId")
        if not event_id:
            print(f"No event ID found in cart item {cart_key}")
            continue

        try:
            event = Event.objects.get(eventId=event_id)
        except Event.DoesNotExist:
            print(f"Event with ID {event_id} not found.")
            continue

        # If this item is a crew ticket
        if "_crew_" in cart_key or "crewId" in ticket_info:
            crew_id = ticket_info["crewId"]
            try:
                crew = Crew.objects.get(crewId=crew_id)
            except Crew.DoesNotExist:
                print(f"Crew with ID {crew_id} not found.")
                continue

            # Generate one ticket for each crew member
            for member in crew.members.all():
                generateTicket(
                    request=request,
                    event=event,
                    user=member if member else None,
                    guestFirstName=member.first_name if member else None,
                    guestLastName=member.last_name if member else None,
                    guestEmail=member.email if member else None,
                    crewTicket=(member != request.user),
                )
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    f"Generated ticket for {member.first_name} {member.last_name}",
                )
        else:
            if request.user.is_authenticated:
                first_name = request.user.first_name
                last_name = request.user.last_name
                email = request.user.email
            else:
                # Split the name on whitespace; you might want to handle unexpected formats
                name_parts = session.customer_details.name.split()
                first_name = name_parts[0] if name_parts else ""
                last_name = name_parts[-1] if len(name_parts) > 1 else ""
                email = session.customer_details.email

            # A normal ticket
            quantity = ticket_info.get("quantity", 1)
            for _ in range(quantity):
                generateTicket(
                    request=request,
                    event=event,
                    user=request.user if request.user.is_authenticated else None,
                    guestFirstName=first_name,
                    guestLastName=last_name,
                    guestEmail=email,
                )

    # Clean up session data
    if "cart" in request.session:
        del request.session["cart"]
    if "checkout_user_info" in request.session:
        del request.session["checkout_user_info"]

    # Render your success page
    return render(request, "eventTicketsApp/checkoutSession/paymentSuccessful.html", {})


def paymentFailed(request):
    return render(request, "eventTicketsApp/checkoutSession/paymentFailed.html")


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

        # Get the cart data from the request
        cart_data = json.loads(request.body)

        # Save the cart data to the session
        request.session["cart"] = cart_data
        return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)


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


def generateTicket(
    request,
    event,
    user=None,
    guestFirstName=None,
    guestLastName=None,
    guestEmail=None,
    crewTicket=False,
):
    ticket = Ticket(
        user=user if user and user.is_authenticated else None,
        event=event,
        guestFirstName=(
            guestFirstName if guestFirstName else user.first_name if user else None
        ),
        guestLastName=(
            guestLastName if guestLastName else user.last_name if user else None
        ),
        guestEmail=guestEmail if guestEmail else user.email if user else None,
    )
    ticket.save()

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
        # Generate the QR code using maker
        qr_code_image = maker.make_qr_code_image(
            data=qr_data, qr_code_options=qr_code_options, force_text=True
        )

        image_io = BytesIO(qr_code_image)
        ticket.qrCodeImage.save(f"{ticket.ticketId}.png", File(image_io), save=True)

        ticket.save()

        ticketMainId = ticket.mainId
        ticketLink = request.build_absolute_uri(
            reverse("eventTickets:viewTicket", kwargs={"mainId": ticketMainId})
        )

        # Prepare email
        if guestEmail or (user and user.email):
            subject = (
                f"{request.user.first_name} bought a ticket for you for {event.title}"
                if crewTicket
                else f"Your Ticket for {event.title}"
            )
            message = (
                "This ticket was bought by a crew member for you!\nYour QR code is attached."
                if crewTicket
                else "Thank you for your purchase!\nYour QR code is attached."
            )
            recipient_list = [guestEmail] if guestEmail else [user.email]
            qrCodeHtml = render_to_string(
                "emailManagement/build_production/emails/eventTicketsApp/ticketEmail.html",
                {"ticketLink": ticketLink},
            )
            from_email = settings.DEFAULT_FROM_EMAIL

            send_mail(
                subject,
                message,
                from_email,
                recipient_list,
                fail_silently=False,
                html_message=qrCodeHtml,
            )
            # Add event to user's purchased events if authenticated
            if request.user.is_authenticated:
                request.user.user_profile.purchased_events.add(event)

    except Exception as e:
        print(f"Error generating QR code: {e}")
    return ticket


def verifyTicket(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            print(request.body)
            ticketId = data.get("ticketId")
            eventId = data.get("eventId")
            status = data.get("status")

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
