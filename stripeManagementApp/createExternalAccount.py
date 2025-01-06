import stripe
from django.conf import settings


from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string


stripe.api_key = settings.STRIPE_SECRET_KEY


class ExternalAccounts:
    def createBankAccount(request,
        stripeAccountId, bankAccountHolderName, bankAccountNumber, bankRoutingNumber
    ):
        try:
            account = stripe.Account.create_external_account(
                stripeAccountId,
                external_account={
                    "object": "bank_account",
                    "country": "US",
                    "currency": "usd",
                    "account_holder_type": "individual",
                    "account_holder_name": bankAccountHolderName,
                    "account_number": bankAccountNumber,
                    "routing_number": bankRoutingNumber,
                },
            )
            messages.success(request, "Bank account added successfully")
            return account  # Returns the actual Stripe account object
        except stripe.error.StripeError as e:
            messages.error(request, f"Error: {e.user_message}")
        return redirect("eventManagement:hostBilling")

    def createCard(stripeAccountId, cardToken):
        card = stripe.Account.create_external_account(
            stripeAccountId,
            external_account=cardToken
        )
        
        return card

    def setDefaultPaymentMethod(request, stripeAccountId, externalAccountId):
        try:
            stripe.Account.modify_external_account(
                stripeAccountId,
                externalAccountId,
                default_for_currency=True,
            )
            return True
        except stripe.error.StripeError as e:
            messages.error(request, f"Error: {e.user_message}")
        return redirect("eventManagement:hostBilling")

    def removePayoutMethod(request, stripeAccountId, externalAccountId):
        try:
            stripe.Account.delete_external_account(
                stripeAccountId,
                externalAccountId,
            )
            messages.success(request, "Payout method removed successfully")
            return True
        except stripe.error.StripeError as e:
            messages.error(request, f"Error: {e.user_message}")
        return redirect("eventManagement:hostBilling")
