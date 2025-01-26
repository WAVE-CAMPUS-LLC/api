import stripe
from django.conf import settings


from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string


stripe.api_key = settings.STRIPE_SECRET_KEY


# The `CustomerAccount` class provides methods for creating customer accounts, searching for customer
# accounts, and setting up payment intents using the Stripe API.
class CustomerAccount:
    def createCustomerAccount(request, email, first_name, last_name):
        try:
            customer = stripe.Customer.create(
                email=email,
                name=f"{first_name} {last_name}",
            )
            return customer
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e.user_message}")
            messages.error(request, f"Error: {e.user_message}")
        except Exception as e:
            print(f"Error: {str(e)}")
        return None

    def searchCustomerAccount(email):
        try:
            customers = stripe.Customer.list(email=email)
            if customers.data:
                print(f"Found existing customer: {customers.data[0].id}")  # Debug print
                return customers.data[0]
            print("No existing customer found.")  # Debug print
            return None
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e.user_message}")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None
        
    def deleteCustomerAccount(customer_id):
        try:
            stripe.Customer.delete(customer_id)
            return True
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e.user_message}")
            return False
        except Exception as e:
            print(f"Error: {str(e)}")
            return False

    def listPaymentMethods(customer_id):
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card",
            )
            payment_methods_list = []
            for payment_method in payment_methods.auto_paging_iter():
                payment_methods_list.append({
                    "id": payment_method.id,
                    "card_brand": payment_method.card.brand,
                    "last4": payment_method.card.last4,
                    "exp_month": payment_method.card.exp_month,
                    "exp_year": payment_method.card.exp_year
                })

            return payment_methods_list
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e.user_message}")
            return None
        except Exception as e:
            print(f"Error: {str(e)}")
            return None

    def setupIntent(request, customer_id):
        try:
            intent = stripe.SetupIntent.create(
                customer=customer_id,
                automatic_payment_methods={"enabled": True},
            )
            return intent
        except stripe.error.StripeError as e:
            return JsonResponse({"error": e.user_message}, status=400)
