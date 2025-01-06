import stripe
from django.conf import settings


from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string


stripe.api_key = settings.STRIPE_SECRET_KEY





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
