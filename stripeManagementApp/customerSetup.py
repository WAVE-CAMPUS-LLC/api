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
            customer = stripe.Customer.retrieve(customer_id)
            default_payment_method = customer.invoice_settings.default_payment_method

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
                    "exp_year": payment_method.card.exp_year,
                    "is_default": payment_method.id == default_payment_method
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
            return redirect("accountManagement:userAccount")
        except stripe.error.StripeError as e:
            messages.error(request, f"Error: {e.user_message}")
            return redirect("accountManagement:userAccount")

    def removePaymentMethod(request, payment_method_id):
        try:
            payment_method = stripe.PaymentMethod.detach(payment_method_id)
            return redirect("accountManagement:userAccount")
        except stripe.error.StripeError as e:
            messages.error(request, {"error": e.user_message})
            return redirect("accountManagement:userAccount")

    def setDefaultPaymentMethod(customer_id, payment_method_id):
        try:
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )

            stripe.Customer.modify(
                customer_id,
                invoice_settings={'default_payment_method': payment_method_id}
            )

            return True
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e.user_message}")
            return False
        except Exception as e:
            print(f"Error: {str(e)}")
            return False

    def cardExists(customer_id, fingerprint):
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card",
            )
            for payment_method in payment_methods.auto_paging_iter():
                if payment_method.card.fingerprint == fingerprint:
                    return True
            return False
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e.user_message}")
            return False
        except Exception as e:
            print(f"Error: {str(e)}")
            return False
        
    def setupPaymentIntent(request, customer_id, amount, currency):
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                customer=customer_id,
                payment_method_types=["card"],
                automatic_payment_methods={"enabled": True},
                setup_future_usage="off_session",
            )
            return intent
        except stripe.error.StripeError as e:
            messages.error(request, f"Error: {e.user_message}")
            return None
        except Exception as e:
            print(f"Error: {str(e)}")
            return None
        
    
class ConnectAccount:
    def createConnectAccount(request, user):
        try:
            account = stripe.Account.create(
                type="express",
                country="US",
                email=user.email,
                capabilities={
                    "card_payments": {
                        "requested": True,
                    },
                    "transfers": {
                        "requested": True,
                    },
                }
            
            )
            
            return account
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e.user_message}")
            return JsonResponse({"error": e.user_message})
        except Exception as e:
            print(f"Error: {str(e)}")
            return JsonResponse({"error": str(e)})
        
    def getStripeOnboardingLink(request, user, domain, finalLink):
        try:
            account_links = stripe.AccountLink.create(
                account=user.connectAccountID,
                refresh_url=f'{domain}/refresh/{user.connectAccountID}',
                return_url=f"{finalLink}",
                type="account_onboarding",
            )
            
            return account_links.url
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e.user_message}")
            return JsonResponse({"error": e.user_message})
        except Exception as e:
            print(f"Error: {str(e)}")
            return JsonResponse({"error": str(e)})

    def getStripeAccountLogin(request, user, domain, finalLink):
        try:
            account_link = stripe.Account.create_login_link(user.connectAccountID)
            
            return account_link.url
        except stripe.error.StripeError as e:
            messages.error(request, f"Stripe error: {e.user_message}")
            return JsonResponse({"error": e.user_message})
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return JsonResponse({"error": str(e)})