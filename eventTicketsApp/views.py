from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
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

from socialApp.models import Crew
from .models import PaidFreeTicket, Ticket, UserPayment, StripePlatformSettings
from eventManagementApp.models import Event, HostProfile


def initialize_stripe_settings():
    """Initialize default Stripe platform settings if they don't exist"""
    if not StripePlatformSettings.objects.exists():
        StripePlatformSettings.objects.create(
            salesTaxPercentage=Decimal('7.00'),  # 8% sales tax
            salesFeeAmount=Decimal('0.99'),      # $2 fee per ticket
            percentageStayingOnPlatform=Decimal('50.0')  # 2.9% platform fee
        )

import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.conf import settings
from decimal import Decimal
import stripe

def checkoutView(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Get the cart from the session
    cart = request.session.get("cart", {})
    if not cart:
        return JsonResponse({"error": "Your cart is empty."}, status=400)

    # Initialize your Stripe platform settings
    initialize_stripe_settings()
    platform_settings = StripePlatformSettings.objects.first()
    if not platform_settings:
        return JsonResponse({"error": "Stripe platform settings not found"}, status=500)

    sales_tax_percentage = platform_settings.salesTaxPercentage
    sales_fee_amount = platform_settings.salesFeeAmount
    percentage_staying_on_platform = platform_settings.percentageStayingOnPlatform

    total_amount = Decimal(0.0)
    host_total = Decimal(0.0)
    adjusted_line_items = []
    event_id = None

    # Calculate totals and build line_items for Stripe
    for _, ticket in cart.items():
        ticket_price = Decimal(ticket["price"])
        ticket_quantity = int(ticket["quantity"])
        event_id = ticket["eventId"]  # We assume all items are for one event

        # Price + tax + fee
        sales_tax = ticket_price * (sales_tax_percentage / Decimal(100))
        final_ticket_price = ticket_price + sales_tax + sales_fee_amount

        total_amount += (final_ticket_price * ticket_quantity)
        host_total += (ticket_price * ticket_quantity)

        adjusted_line_items.append(
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "Event Ticket"},
                    "unit_amount": int(final_ticket_price * 100),
                },
                "quantity": ticket_quantity,
            }
        )

    if not event_id:
        return JsonResponse({"error": "Event ID not found in cart."}, status=400)

    event = get_object_or_404(Event, eventId=event_id)
    host_profile = get_object_or_404(HostProfile, user=event.host)
    host_stripe_account_id = host_profile.stripe_account_id

    if request.method == "POST":
        # ------------------------------
        # 1) Parse Guest Info or Use Authenticated Info
        # ------------------------------
        if request.user.is_authenticated:
            # Authenticated user
            customer_email = request.user.email
            customer_metadata = {
                "Customer Name": f"{request.user.first_name} {request.user.last_name}",
                "Customer Email": request.user.email,
            }
        else:
            # Guest user => read JSON or form data
            if request.content_type == "application/json":
                # Parse JSON
                try:
                    data = json.loads(request.body)
                except json.JSONDecodeError:
                    return JsonResponse({"error": "Invalid JSON data."}, status=400)
                
                first_name = data.get("first_name")
                last_name = data.get("last_name")
                email = data.get("email")
            else:
                # Fallback if you're sometimes posting via traditional HTML form
                first_name = request.POST.get("first_name")
                last_name = request.POST.get("last_name")
                email = request.POST.get("email")

            # Validate guest info
            if not all([first_name, last_name, email]):
                return JsonResponse({"error": "Complete guest information is required."}, status=400)

            customer_email = email
            customer_metadata = {
                "Customer Name": f"{first_name} {last_name}",
                "Customer Email": email,
            }

        # ------------------------------
        # 2) Create Stripe Customer
        # ------------------------------
        try:
            customer = stripe.Customer.create(
                email=customer_email,
                metadata=customer_metadata
            )

            # Calculate application fee
            application_fee_amount = host_total * percentage_staying_on_platform / Decimal(100)

            # Your success and cancel URLs
            load_dotenv()
            # domain = os.getenv("WEBSITE_DOMAIN")  # e.g. "http://127.0.0.1:8000"
            domain = "http://127.0.0.1:8000"


            # ------------------------------
            # 3) Create the Stripe Checkout Session
            # ------------------------------
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=adjusted_line_items,
                mode="payment",
                success_url=f"{domain}/paymentSuccessful/?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{domain}/paymentFailed/",
                customer=customer.id,
                payment_intent_data={
                    "on_behalf_of": host_stripe_account_id,
                    "application_fee_amount": int(application_fee_amount * 100),
                    "transfer_data": {"destination": host_stripe_account_id},
                },
            )

            return JsonResponse({"url": checkout_session.url})

        except stripe.error.StripeError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)

    # If not POST, render your checkout page
    return render(
        request,
        "eventTicketsApp/checkoutSession/checkout.html",
        {"cart": cart, "total_amount": total_amount},
    )



def paymentSuccessful(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    checkout_session_id = request.GET.get("session_id")

    if checkout_session_id:
        session = stripe.checkout.Session.retrieve(checkout_session_id)
        customer = stripe.Customer.retrieve(session.customer)

        # Mark the payment as successful
        user_payment = UserPayment.objects.create(
            user=request.user if request.user.is_authenticated else None,
            stripe_checkout_id=checkout_session_id,
            success=True
        )

        # Retrieve the cart from the session
        cart = request.session.get("cart", {})

        # If you collected guest info during checkout:
        user_info = request.session.get("checkout_user_info", {})

        # Go through each cart item to generate tickets
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

            # -------------------------------------------------
            # Check if this item is a "crew" ticket or regular
            # -------------------------------------------------
            if "_crew_" in cart_key or "crewId" in ticket_info:
                # A CREW TICKET
                crew_id = ticket_info["crewId"]
                try:
                    crew = Crew.objects.get(crewId=crew_id)
                except Crew.DoesNotExist:
                    print(f"Crew with ID {crew_id} not found.")
                    continue

                # Generate one ticket *for each member* of the crew
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
                    messages.add_message(request, messages.SUCCESS, f"Generated ticket for {member.first_name} {member.last_name}")
                    print(f"Generated ticket for {member.first_name} {member.last_name}")
                    print(f"Generated ticket for {member.first_name} {member.last_name}")
                    print(f"Generated ticket for {member.first_name} {member.last_name}")
            else:
                # A REGULAR TICKET
                quantity = ticket_info["quantity"]

                # Create N tickets (for user or guest)
                for _ in range(quantity):
                    generateTicket( 
                        request=request,
                        event=event,
                        user=(request.user if request.user.is_authenticated else None),
                        guestFirstName=user_info.get("first_name"),
                        guestLastName=user_info.get("last_name"),
                        guestEmail=user_info.get("email"),
                    )

        # Clean up session
        if "cart" in request.session:
            del request.session["cart"]
        if "checkout_user_info" in request.session:
            del request.session["checkout_user_info"]

        return render(
            request,
            "eventTicketsApp/checkoutSession/paymentSuccessful.html",
            {
                "customer": customer,
                "customerUsername": customer.metadata.get("username"),
            },
        )

    return JsonResponse({"error": "Session ID not provided."}, status=400)



def paymentFailed(request):
    return render(request, "eventTicketsApp/checkoutSession/paymentFailed.html")


@csrf_exempt
def stripeWebhook(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET_TEST
    time.sleep(10)
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

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session.get("id", None)
        time.sleep(15)
        user_payment = UserPayment.objects.get(stripe_checkout_id=session_id)
        line_items = stripe.checkout.Session.list_line_items(session_id, limit=1)
        user_payment.success = True
        user_payment.save()
    return HttpResponse(status=200)


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
    request, event, user=None, guestFirstName=None, guestLastName=None, guestEmail=None, crewTicket=False
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
                if crewTicket else
                f"Your Ticket for {event.title}"
            )
            message = (
                "This ticket was bought by a crew member for you!\nYour QR code is attached."
                if crewTicket else
                "Thank you for your purchase!\nYour QR code is attached."
            )
            recipient_list = [guestEmail] if guestEmail else [user.email]
            qrCodeHtml = render_to_string("emailManagement/build_production/emails/transactional.html")
            from_email = settings.DEFAULT_FROM_EMAIL

            send_mail(
                subject,
                message,
                from_email,
                recipient_list,
                fail_silently=False,
                html_message=qrCodeHtml,
            )

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
