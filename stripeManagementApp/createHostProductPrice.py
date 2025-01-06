import stripe
from django.conf import settings


from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string


stripe.api_key = settings.STRIPE_SECRET_KEY


def createProductPriceType(eventStripeProductId, price, stripeAccountID, quantity):
    """
    Creates a new price for a product in Stripe.
    """
    try:
        print("Product ID: ", eventStripeProductId)
        product = stripe.Product.retrieve(
            eventStripeProductId, stripe_account=stripeAccountID
        )
        price = stripe.Price.create(
            product=product.id,
            unit_amount=int(price * 100),
            currency="usd",
            stripe_account=stripeAccountID,
            metadata={"product_id": eventStripeProductId, "Quantity":quantity},
        )
        return price
    except stripe.error.InvalidRequestError as e:
        print(f"Stripe Error: {e}")
        raise
