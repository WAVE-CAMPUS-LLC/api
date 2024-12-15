import stripe
from cryptography.fernet import Fernet
from django.conf import settings


from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string


stripe.api_key = settings.STRIPE_SECRET_KEY




def removeStripeAccount(stripeAccountId):
    try:
        stripe.Account.delete(stripeAccountId)
        return {"status": "success"}
    except stripe.error.StripeError as e:
        return {"status": "error", "message": str(e)}