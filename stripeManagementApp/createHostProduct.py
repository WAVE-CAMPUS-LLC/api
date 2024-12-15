import stripe
from cryptography.fernet import Fernet
from django.conf import settings


from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string



stripe.api_key = settings.STRIPE_SECRET_KEY

def createHostProduct(event, stripeAccountId):
    try:
        product = stripe.Product.create(
            name=event.title,
            unit_label="hour",
            statement_descriptor=event.title,  # Stripe allows max 22 characters for statement descriptor
            description=event.description,
            metadata={
                "Event ID": event.eventId, 
                "Date of Event": str(event.date), 
                "Host Profile ID": event.host.id
            },
            stripe_account=stripeAccountId,
        )
        return product  # Returns the actual Stripe product object
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")  # Log the error
        return None  # Return None in case of error
