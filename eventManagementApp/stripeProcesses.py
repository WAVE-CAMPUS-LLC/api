import stripe
from cryptography.fernet import Fernet
from django.conf import settings


from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string


stripe.api_key = settings.STRIPE_SECRET_KEY


def updateConnectWithStripeDetails(hostProfile, update_data):
    try:
        # Update business profile
        if "business_profile.url" in update_data:
            stripe.Account.modify(
                hostProfile.stripe_account_id,
                business_profile={
                    "url": update_data["business_profile.url"],
                },
            )

        if "business_profile" in update_data:
            stripe.Account.modify(
                hostProfile.stripe_account_id,
                business_profile={
                    "business_name": update_data["business_profile.business_name"],
                    "support_phone": update_data["business_profile.support_phone"],
                    "support_email": update_data["business_profile.support_email"],
                    "support_url": update_data["business_profile.support_url"],
                    "product_description": update_data[
                        "business_profile.product_description"
                    ],
                    "support_address": {
                        "line1": update_data["business_profile.support_address"][
                            "line1"
                        ],
                        "city": update_data["business_profile.support_address"]["city"],
                        "state": update_data["business_profile.support_address"][
                            "state"
                        ],
                        "postal_code": update_data["business_profile.support_address"][
                            "postal_code"
                        ],
                        "country": update_data["business_profile.support_address"][
                            "country"
                        ],
                    },
                },
            )

        # Add/update bank account details
        if "bank_details" in update_data:
            stripe.Account.create_external_account(
                hostProfile.stripe_account_id,
                external_account={
                    "object": "bank_account",
                    "country": "US",
                    "currency": "usd",
                    "account_holder_name": update_data["bank_details"][
                        "account_holder_name"
                    ],
                    "account_holder_type": "individual",
                    "account_number": update_data["bank_details"]["account_number"],
                    "routing_number": update_data["bank_details"]["routing_number"],
                },
            )

        if "individual.first_name" in update_data:
            stripe.Account.modify(
                hostProfile.stripe_account_id,
                individual={"first_name": update_data["individual.first_name"]},
            )

        if "individual.last_name" in update_data:
            stripe.Account.modify(
                hostProfile.stripe_account_id,
                individual={"last_name": update_data["individual.last_name"]},
            )

        if (
            "individual.dob.day" in update_data
            or "individual.dob.month" in update_data
            or "individual.dob.year" in update_data
        ):
            stripe.Account.modify(
                hostProfile.stripe_account_id,
                individual={
                    "dob": {
                        "day": update_data["individual.dob.day"],
                        "month": update_data["individual.dob.month"],
                        "year": update_data["individual.dob.year"],
                    }
                },
            )

        if "individual.ssn_last_4" in update_data:
            stripe.Account.modify(
                hostProfile.stripe_account_id,
                individual={
                    "ssn_last_4": update_data["individual.ssn_last_4"],
                },
            )
        # Update personal details
        if "address" in update_data:
            stripe.Account.modify(
                hostProfile.stripe_account_id,
                individual={
                    "address": {
                        "line1": update_data["address"]["line1"],
                        "city": update_data["address"]["city"],
                        "state": update_data["address"]["state"],
                        "postal_code": update_data["address"]["postal_code"],
                        "country": update_data["address"]["country"],
                    },
                },
            )

        # Accept terms of service
        if "tos_acceptance" in update_data:
            tos_data = update_data["tos_acceptance"]

            tos_acceptance = {
                "date": tos_data["date"],
                "ip": tos_data["ip"],
                "user_agent": tos_data["user_agent"],
                "service_agreement": tos_data["service_agreement"],
            }

            stripe.Account.modify(
                hostProfile.stripe_account_id, tos_acceptance=tos_acceptance
            )

        return {"status": "success"}
    except stripe.error.StripeError as e:
        print("message", str(e))
        return {"status": "error", "message": str(e)}


def getRequiredActions(stripeAccountId):
    try:
        # Retrieve the Stripe account using the account ID
        account = stripe.Account.retrieve(stripeAccountId)

        if "requirements" in account:
            requirements = account["requirements"]

            # Extract all required actions: currently_due, eventually_due, and pending_verification
            currently_due = requirements.get("currently_due", [])
            eventually_due = requirements.get("eventually_due", [])
            pending_verification = requirements.get("pending_verification", [])

            # Combine all required actions into one list
            all_required_actions = list(
                set(currently_due + eventually_due + pending_verification)
            )

            # Clean up the actions list (remove duplicates)
            print(f"All required actions: {all_required_actions}")
            return {"status": "success", "required_actions": all_required_actions}

        # If 'requirements' field is missing, handle it
        return {"status": "error", "message": "No requirements data available"}

    except stripe.error.StripeError as e:
        # Handle any Stripe API errors
        return {"status": "error", "message": str(e)}


def removeStripeAccount(stripeAccountId):
    try:
        stripe.Account.delete(stripeAccountId)
        return {"status": "success"}
    except stripe.error.StripeError as e:
        return {"status": "error", "message": str(e)}


# removeStripeAccount("acct_1QVZkiIijVu7hMzN")
