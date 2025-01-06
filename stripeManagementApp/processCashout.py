import stripe
from django.conf import settings


from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string



stripe.api_key = settings.STRIPE_SECRET_KEY


class CashoutRequest:
    def getExternalAccountId(accountId):
        try:
            external_accounts = stripe.Account.list_external_accounts(
                accountId,
                object="bank_account",  # Can also be "card" if you allow debit cards
            )
            if external_accounts.data:
                return external_accounts.data[0].id  # Use the first external account
            return None
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e.user_message}")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

    def processCashoutRequest(amount, currency, accountId):
        try:
            transfer = stripe.Payout.create(
                amount=amount,
                currency=currency,
                stripe_account=accountId,
            )
            return transfer
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e.user_message}")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None
        return None