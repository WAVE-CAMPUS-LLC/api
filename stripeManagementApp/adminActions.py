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

def format_timestamp(unix_timestamp):
        """Convert UNIX timestamp to a custom human-readable date string."""
        return datetime.utcfromtimestamp(unix_timestamp).strftime('%d %b, %H:%M')

class StripeAdmin:
    def getConnectedAccounts(request):
        try:
            # List all connected accounts
            accounts = stripe.Account.list()
            accounts_with_balance = []

            for account in accounts["data"]:
                try:
                    # Retrieve the balance for the connected account
                    balance = stripe.Balance.retrieve(stripe_account=account["id"])
                    available_balance = sum(
                        [b["amount"] / 100 for b in balance.get("available", [])]
                    )  # Convert cents to dollars for available balance
                    pending_balance = sum(
                        [b["amount"] / 100 for b in balance.get("pending", [])]
                    )  # Convert cents to dollars for pending balance
                except stripe.error.StripeError:
                    available_balance = 0  # Default to 0 if balance retrieval fails
                    pending_balance = 0  # Default to 0 if retrieval fails

                # Get the created timestamp and format it
                created_timestamp = account.get("created")
                connected_date = format_timestamp(created_timestamp)

                # Append the account data with balance and connected date information
                account_data = {
                    "id": account["id"],
                    "individual": account.get("individual"),
                    "email": account.get("email"),
                    "charges_enabled": account.get("charges_enabled"),
                    "payouts_enabled": account.get("payouts_enabled"),
                    "available_balance": available_balance,
                    "pending_balance": pending_balance,
                    "connected_date": connected_date,  # Add formatted connected date
                }
                accounts_with_balance.append(account_data)

            return accounts_with_balance
        except stripe.error.StripeError as e:
            messages.error(request, f"Error: {e}")
            return []