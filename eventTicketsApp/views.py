from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
import uuid
from io import BytesIO
from decimal import Decimal
from django.core.files import File
import json
import os
import time
from qr_code.qrcode import maker
from qr_code.qrcode.utils import QRCodeOptions
import stripe
from .models import PaidFreeTicket, Ticket, UserPayment, StripePlatformSettings
from eventManagementApp.models import Event, HostProfile
from socialApp.models import Crew, CrewMember
from django.views.decorators.http import require_POST


def checkoutView(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    cart = request.session.get("cart", {})
    event_id = None
    platform_settings = StripePlatformSettings.objects.first()

    if not platform_settings:
        return JsonResponse({"error": "Stripe platform settings not found"}, status=500)

    sales_tax_percentage = platform_settings.salesTaxPercentage
    sales_fee_amount = platform_settings.salesFeeAmount

    # Calculate totals and ensure single-event assumption
    total_amount = Decimal(0.0)
    host_total = Decimal(0.0)
    adjusted_line_items = []
    event_id = None

    for _, ticket in cart.items():
        ticket_price = Decimal(ticket["price"])
        ticket_quantity = int(ticket["quantity"])
        event_id = ticket["eventId"]  # Assumes all tickets are for the same event

        # Calculate sales tax and final ticket price
        sales_tax = ticket_price * (sales_tax_percentage / Decimal(100))
        final_ticket_price = ticket_price + sales_tax + sales_fee_amount

        # Update totals
        total_amount += final_ticket_price * ticket_quantity
        host_total += ticket_price * ticket_quantity

        # Add item to Stripe line items
        adjusted_line_items.append(
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "Event Ticket"},
                    "unit_amount": int(final_ticket_price * 100),  # Stripe uses cents
                },
                "quantity": ticket_quantity,
            }
        )

    if not event_id:
        return JsonResponse({"error": "Event ID not found in cart."}, status=400)

    # Retrieve event and host details
    event = get_object_or_404(Event, eventId=event_id)
    host = event.host
    hostProfile = get_object_or_404(HostProfile, user=host)
    hostStripeAccountId = hostProfile.stripe_account_id

    if not hostStripeAccountId:
        return JsonResponse({"error": "Host has not set up their payment account yet."}, status=400)

    # Verify host's Stripe account capabilities
    try:
        account = stripe.Account.retrieve(hostStripeAccountId)
        if not account.charges_enabled:
            return JsonResponse({"error": "Host's payment account is not fully set up to accept payments."}, status=400)
    except stripe.error.StripeError as e:
        return JsonResponse({"error": "Unable to verify host's payment account."}, status=400)

    # Customer information
    if request.user.is_authenticated:
        customerEmail = request.user.email
        customer_metadata = {
            "Customer Name": f"{request.user.first_name} {request.user.last_name}",
            "Customer Email": customerEmail,
        }
    else:
        guest_info = {
            "first_name": request.POST.get("first_name"),
            "last_name": request.POST.get("last_name"),
            "email": request.POST.get("email"),
        }

        if not all(guest_info.values()):
            return JsonResponse(
                {"error": "Complete guest information is required."}, status=400
            )

        customerEmail = guest_info["email"]
        customer_metadata = {
            "Customer Name": f"{guest_info['first_name']} {guest_info['last_name']}",
            "Customer Email": customerEmail,
        }

    if request.method == "POST":
        try:
            # Create a Stripe customer
            customer = stripe.Customer.create(
                email=customerEmail, metadata=customer_metadata
            )

            # Calculate application fee
            application_fee_amount = (
                host_total
                * platform_settings.percentageStayingOnPlatform
                / Decimal(100)
            )

            # Create Stripe checkout session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=adjusted_line_items,
                mode="payment",
                success_url=request.build_absolute_uri(reverse('eventTickets:paymentSuccessful')) + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=request.build_absolute_uri(reverse('eventTickets:paymentFailed')),
                customer=customer.id,
                payment_intent_data={
                    "application_fee_amount": int(application_fee_amount * 100),
                    "transfer_data": {"destination": hostStripeAccountId},
                },
            )

            return JsonResponse({"url": checkout_session.url})

        except stripe.error.StripeError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Exception as e:
            return JsonResponse({"error": "An unexpected error occurred."}, status=500)

    return render(
        request,
        "eventTicketsApp/checkoutSession/checkout.html",
        {"cart": cart, "total_amount": total_amount},
    )


def paymentSuccessful(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    checkout_session_id = request.GET.get("session_id", None)

    if checkout_session_id:
        session = stripe.checkout.Session.retrieve(checkout_session_id)
        customer = stripe.Customer.retrieve(session.customer)

        user_payment = UserPayment.objects.create(
            user=request.user if request.user.is_authenticated else None,
            stripe_checkout_id=checkout_session_id,
        )
        user_payment.success = True
        user_payment.save()

        user_info = request.session.get("checkout_user_info", {})
        cart = request.session.get("cart", {})

        for ticket_id, ticket in cart.items():
            eventId = ticket.get("eventId")
            if eventId:
                try:
                    event = Event.objects.get(eventId=eventId)
                    for _ in range(ticket["quantity"]):
                        generateTicket(
                            request=request,
                            event=event,
                            user=(
                                request.user if request.user.is_authenticated else None
                            ),
                            guestFirstName=user_info.get("first_name"),
                            guestLastName=user_info.get("last_name"),
                            guestEmail=user_info.get("email"),
                        )
                except Event.DoesNotExist:
                    print(f"Event with ID {eventId} not found.")
            else:
                print(f"Event ID not found for ticket: {ticket}")

        # Safely delete session keys
        if "cart" in request.session:
            del request.session["cart"]
        if "checkout_user_info" in request.session:
            del request.session["checkout_user_info"]

        customer_username = customer.metadata.get("username")
        return render(
            request,
            "eventTicketsApp/checkoutSession/paymentSuccessful.html",
            {"customer": customer, "customerUsername": customer_username},
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
    request, event, user=None, guestFirstName=None, guestLastName=None, guestEmail=None
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
            recipient_list = [guestEmail] if guestEmail else [user.email]
            subject = f"Your Ticket for {event.title}"
            qrCodeHtml = render_to_string(
                "emailTemplates/eventTicketsApp/ticketQRCode.html",
                {"ticketLink": ticketLink, "event": event},
            )
            message = f"Thank you for your purchase!\n" f"Your QR code is attached."
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


@login_required
@require_POST
def crewPurchaseView(request):
    try:
        data = json.loads(request.body)
        crew_id = data.get('crewId')
        ticket_id = data.get('ticketId')
        
        if not crew_id or not ticket_id:
            return JsonResponse({
                'success': False,
                'error': 'Missing crew ID or ticket ID'
            }, status=400)
        
        # Get the crew and count members
        crew = get_object_or_404(Crew, crewId=crew_id)
        crew_size = CrewMember.objects.filter(crew=crew).count()
        
        if crew_size == 0:
            return JsonResponse({
                'success': False,
                'error': 'No members found in the crew'
            }, status=400)
        
        # Get the ticket and event details
        ticket = get_object_or_404(PaidFreeTicket, ticket_id=ticket_id)
        event = ticket.event
        
        # Calculate discounted price if applicable
        ticket_price = Decimal(str(ticket.ticket_price))
        if event.crew_discount and crew_size >= event.minimum_crew_size:
            discount_percentage = Decimal(str(event.crew_discount_percentage))
            ticket_price = ticket_price * (1 - discount_percentage / 100)
        
        # Create cart entry for the crew
        cart = request.session.get('cart', {})
        cart[ticket_id] = {
            'name': ticket.ticket_name,
            'price': str(ticket_price),
            'quantity': crew_size,
            'priceId': ticket.stripePriceId,
            'productId': event.stripeProductId,
            'eventId': str(event.eventId),
            'eventTitle': event.title,
            'isCrewPurchase': True,
            'crewId': str(crew_id),
            'crewSize': crew_size,
            'originalPrice': str(ticket.ticket_price),
            'discountApplied': event.crew_discount and crew_size >= event.minimum_crew_size,
            'discountPercentage': str(event.crew_discount_percentage if event.crew_discount else 0)
        }
        
        request.session['cart'] = cart
        request.session.modified = True
        
        checkout_url = reverse('eventTickets:checkout')
        
        return JsonResponse({
            'success': True,
            'message': f'Added {crew_size} tickets for crew {crew.name}',
            'redirectUrl': request.build_absolute_uri(checkout_url)
        })
        
    except Crew.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Crew not found'
        }, status=404)
    except PaidFreeTicket.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Ticket not found'
        }, status=404)
    except Exception as e:
        print(f"Error in crewPurchaseView: {str(e)}")  # Add logging
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
