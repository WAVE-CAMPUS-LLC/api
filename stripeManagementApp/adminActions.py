import stripe
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
    return datetime.utcfromtimestamp(unix_timestamp).strftime("%d %b, %H:%M")


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

    def getConnectedAccountDetails(request, account_id):
        try:
            # Retrieve the connected account details
            account = stripe.Account.retrieve(account_id)

            # Format TOS acceptance date
            tos_acceptance = account.get("tos_acceptance", {})
            tos_acceptance_date = tos_acceptance.get("date")
            formatted_date = (
                datetime.utcfromtimestamp(tos_acceptance_date).strftime("%Y-%m-%d %H:%M:%S")
                if tos_acceptance_date
                else None
            )

            # Check if SSN last 4 digits are provided
            individual = account.get("individual", {})
            ssn_last_4_provided = individual.get("ssn_last_4")

            # Construct account details dictionary
            account_details = {
                "id": account["id"],
                "type": account.get("type"),  # 'standard', 'express', or 'custom'
                "email": account.get("email"),
                "charges_enabled": account.get("charges_enabled"),
                "payouts_enabled": account.get("payouts_enabled"),
                "country": account.get("country"),
                "business_profile": account.get("business_profile"),  # Business details
                "individual": {
                    "ssn_last_4_provided": ssn_last_4_provided,
                    "first_name": individual.get("first_name"),
                    "last_name": individual.get("last_name"),
                    "phone": individual.get("phone"),
                    "website": individual.get("website"),
                },
                "created": account.get("created"),  # Account creation timestamp
                "capabilities": account.get("capabilities"),  # Account capabilities
                "requirements": account.get("requirements"),
                "settings": account.get("settings"),  # Account settings
                "tos_acceptance": {
                    "date": formatted_date,
                    "ip": tos_acceptance.get("ip"),
                    "user_agent": tos_acceptance.get("user_agent"),
                    "service_agreement": tos_acceptance.get("service_agreement"),
                },
            }

            return account_details

        except stripe.error.InvalidRequestError as e:
            messages.error(request, f"Invalid request: {e}")
            return {}
        except stripe.error.AuthenticationError as e:
            messages.error(request, f"Authentication error: {e}")
            return {}
        except stripe.error.StripeError as e:
            messages.error(request, f"Stripe error: {e}")
            return {}
        except Exception as e:
            messages.error(request, f"Unexpected error: {e}")
            return {}
        
        
    def getConnectedAccountTransactions(request, account_id):
        try:
            # Retrieve the connected account transactions
            transactions = stripe.BalanceTransaction.list(stripe_account=account_id)

            # Construct a list of transactions with formatted data
            formatted_transactions = []
            for transaction in transactions["data"]:
                formatted_transaction = {
                    "id": transaction["id"],
                    "amount": transaction.get("amount") / 100,  # Convert cents to dollars
                    "currency": transaction.get("currency"),
                    "type": transaction.get("type"),
                    "status": transaction.get("status"),
                    "created": format_timestamp(transaction.get("created")),
                }
                formatted_transactions.append(formatted_transaction)

            return formatted_transactions

        except stripe.error.StripeError as e:
            messages.error(request, f"Error: {e}")
            return []
        
        
    def getProducts(request):
        try:
            # List all products
            products = stripe.Product.list()["data"]

            # Enhance product data with prices and formatted creation date
            for product in products:
                # Fetch prices for the product
                prices = stripe.Price.list(product=product["id"])["data"]
                product["prices"] = prices  # Add prices to the product

                # Log debugging information
                if not prices:
                    print(f"No prices found for product: {product['name']} (ID: {product['id']})")
                else:
                    for price in prices:
                        print(f"Price for product {product['name']}: {price}")

                # Format the creation timestamp
                created_timestamp = product.get("created")
                product["formatted_created"] = (
                    datetime.utcfromtimestamp(created_timestamp).strftime("%Y-%m-%d %H:%M:%S")
                    if created_timestamp
                    else None
                )

            return products
        except stripe.error.StripeError as e:
            messages.error(request, f"Error: {e}")
            return []
        
        
    def removeStripeAccount(request, stripeAccountId):
        try:
            stripe.Account.delete(stripeAccountId)
            messages.success(request, "Stripe account deleted successfully.")
            return {"status": "success"}
        except stripe.error.StripeError as e:
            messages.error(request, f"Error: {e}")
            return {"status": "error", "message": str(e)}
        
    def rejectStripeAccount(request, stripeAccountId):
        try:
            stripe.Account.reject(stripeAccountId, reason="other")
            messages.success(request, "Stripe account rejected successfully.")
            return {"status": "success"}
        except stripe.error.StripeError as e:
            messages.error(request, f"Error: {e}")
            return {"status": "error", "message": str(e)}