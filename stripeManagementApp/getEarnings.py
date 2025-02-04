import stripe
from django.conf import settings


from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string



stripe.api_key = settings.STRIPE_SECRET_KEY


class GetEarnings:
    def getStripeAccountBalance(stripeAccountId):
        try:
            balance = stripe.Balance.retrieve(stripe_account=stripeAccountId)
            
            available_balance = sum(item["amount"] for item in balance["available"]) / 100
            pending_balance = sum(item["amount"] for item in balance["pending"]) / 100
            
            return {
                "available": available_balance,
                "pending": pending_balance,
            }
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e}")
            return {"available": 0, "pending": 0}
    
    
    def getTotalEarnings(stripeAccountId):
        try:
            earnings = stripe.Charge.list(stripe_account=stripeAccountId)
            total_earnings = sum(earning.amount for earning in earnings['data'])/100
            return total_earnings
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e}")
            return 0
        
    def requestPayout(stripeAccountId, amount):
        try:
            balance = stripe.Balance.retrieve(stripe_account=stripeAccountId)
            instant_available = balance["instant_available"][0]["amount"] if balance["instant_available"] else 0

            if amount > instant_available:
                print(f"Error: Requested payout amount ({amount}) exceeds instant available balance ({instant_available}).")
                return None

            payout = stripe.Payout.create(
                amount=amount,
                currency="usd",
                stripe_account=stripeAccountId,
                method="instant",
            )
            return payout
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e}")
            return None
        except Exception as e:
            print(f"Error: {str(e)}")
            return None
        
    