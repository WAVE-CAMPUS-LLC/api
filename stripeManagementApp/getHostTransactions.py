import stripe
from cryptography.fernet import Fernet
from django.conf import settings
from datetime import datetime


from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string


stripe.api_key = settings.STRIPE_SECRET_KEY


class Transactions:
    def getHostTransactions(request, stripeAccountId):
        try:
            transactions = stripe.BalanceTransaction.list(
                stripe_account=stripeAccountId
            )

            grouped_transactions = {}
            for transaction in transactions.data:
                # Convert amount to dollars
                transaction.amount_in_dollars = transaction.amount / 100

                # Add human-readable date
                transaction.created_readable = datetime.fromtimestamp(transaction.created)
                date = transaction.created_readable.strftime("%B %d, %Y")
                
                # Ensure we are retrieving the charge ID (payment ID)
                if hasattr(transaction, 'charge') and transaction.charge:
                    transaction.payment_id = transaction.charge
                else:
                    transaction.payment_id = None  # In case there's no charge ID

                # Group transactions by date
                if date in grouped_transactions:
                    grouped_transactions[date].append(transaction)
                else:
                    grouped_transactions[date] = [transaction]

            return grouped_transactions
        except stripe.error.StripeError as e:
            messages.error(request, f"Error: {e.user_message}")
        return redirect("eventManagement:hostBilling")


    
    def getHostPayouts(request, stripeAccountId):
        try:
            payouts = stripe.Payout.list(
                stripe_account=stripeAccountId
            )
            
            grouped_payouts = {}
            for payout in payouts.data:
                payout.amount_in_dollars = payout.amount / 100
                payout.created_readable = datetime.fromtimestamp(payout.created)
                date = payout.created_readable.strftime("%B %d, %Y")
                if date in grouped_payouts:
                    grouped_payouts[date].append(payout)
                else:
                    grouped_payouts[date] = [payout]
            return grouped_payouts 
        except stripe.error.StripeError as e:
            messages.error(request, f"Error: {e.user_message}")
        return redirect("eventManagement:hostBilling")
    
    
    def processRefund(request, stripeAccountId, chargeId):
        try:
            refund = stripe.Refund.create(
                charge=chargeId,
                stripe_account=stripeAccountId
            )
            if refund.status == "succeeded":
                print("Refund successful")
                messages.success(request, "Refund successful")
            return refund
        except stripe.error.StripeError as e:
            print(f"Error: {e}")
            messages.error(request, f"Error: {e}")
        return redirect("eventManagement:hostBilling")