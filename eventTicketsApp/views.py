from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
import uuid
from io import BytesIO
from django.core.files import File
import json
import os
from qr_code.qrcode import maker
from qr_code.qrcode.utils import QRCodeOptions
from .models import Ticket


# Create your views here.
def checkoutView(request):
    cart = request.session.get("cart", {})

    total_amount = sum(ticket["price"] * ticket["quantity"] for ticket in cart.values())

    # if request.method == 'POST':
    #     # Handle the form submission for payment
    #     payment_info = request.POST
    #     if process_payment(payment_info):  # Implement your payment processing logic
    #         return redirect('payment_success')  # Change this to your success page URL
    #     return render(request, "eventTicketsApp/checkout.html", {'error': 'Payment processing failed.', 'cart': cart, 'total_amount': total_amount})
    return render(
        request,
        "eventTicketsApp/checkout.html",
        {"cart": cart, "total_amount": total_amount},
    )


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
            request, "eventTicketsApp/ticket/viewTicket.html", {"ticket": ticket, "event": event}
        )
    else:
        return redirect("core:explore")


def generateTicket(
    request, event, user=None, guestFirstName=None, guestLastName=None, guestEmail=None
):
    ticket = Ticket(
        user=user if user and user.is_authenticated else None,
        event=event,
        guestFirstName=guestFirstName,
        guestLastName=guestLastName,
        guestEmail=guestEmail,
    )
    ticket.save()

    qr_data = (
        f"Ticket ID: {ticket.ticketId} | Event: {event.title} | Status: {ticket.status} | Attendee: {ticket.guestFirstName} {ticket.guestLastName}"
    )

    qr_code_options = QRCodeOptions(
        size=200,
        border=4,
        error_correction="H",
        image_format="png",
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
                {"ticketLink":ticketLink, "event": event},
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
