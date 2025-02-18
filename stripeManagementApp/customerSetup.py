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
            if not intent.invoice:
                try:
                    invoice = stripe.Invoice.create(
                        customer=customer_id,
                        auto_advance=True,
                        payment_intent=intent.id,
                    )
                except stripe.error.StripeError as e:
                    messages.error(request, f"Error: {e.user_message}")
                    return None
            return intent
        except stripe.error.StripeError as e:
            messages.error(request, f"Error: {e.user_message}")
            return None
        except Exception as e:
            print(f"Error: {str(e)}")
            return None
        
    def getCustomerTransactions(request, customer_id):
        if not customer_id:
            messages.error(request, "No customer ID provided")
            return []
            
        try:
            charges = []
            processed_ids = set()  # Keep track of processed transaction IDs
            
            # Get payment intents
            payment_intents = stripe.PaymentIntent.list(
                customer=customer_id,
                limit=100,  # Increased limit to get more transactions
                expand=['data.latest_charge']  # Expand charge data
            )
            
            # Process payment intents
            for payment in payment_intents.data:
                if payment.id in processed_ids:
                    continue
                    
                amount = payment.amount / 100  # Convert cents to dollars
                
                # Get charge details if available
                charge = payment.latest_charge if hasattr(payment, 'latest_charge') else None
                
                # Get receipt URL from charge
                receipt_url = charge.receipt_url if charge else None
                
                # If no receipt URL but has invoice, get invoice URL
                if not receipt_url and payment.invoice:
                    try:
                        invoice = stripe.Invoice.retrieve(payment.invoice)
                        receipt_url = invoice.hosted_invoice_url
                    except:
                        receipt_url = None
                
                # If still no URL, use Stripe Dashboard link
                if not receipt_url:
                    receipt_url = f"https://dashboard.stripe.com/payments/{payment.id}"
                
                transaction = {
                    "id": payment.id,
                    "receipt_url": receipt_url,
                    "amount": amount,
                    "currency": payment.currency,
                    "status": payment.status,
                    "created": payment.created,
                    "description": payment.description or "Payment",
                    "payment_method_details": charge.payment_method_details if charge else None
                }
                
                charges.append(transaction)
                processed_ids.add(payment.id)
                if charge:
                    processed_ids.add(charge.id)
            
            # Process direct charges that might not be associated with payment intents
            direct_charges = stripe.Charge.list(
                customer=customer_id,
                limit=100
            )
            
            # Process direct charges that might not be associated with payment intents
            for charge in direct_charges.data:
                # Skip if this charge is already included via payment intent
                if charge.id in processed_ids or (charge.payment_intent and charge.payment_intent in processed_ids):
                    continue
                    
                transaction = {
                    "id": charge.id,
                    "receipt_url": charge.receipt_url,
                    "amount": charge.amount / 100,
                    "currency": charge.currency,
                    "status": charge.status,
                    "created": charge.created,
                    "description": charge.description or "Payment",
                    "payment_method_details": charge.payment_method_details
                }
                
                charges.append(transaction)
                processed_ids.add(charge.id)
            
            # Sort all transactions by creation date, newest first
            charges.sort(key=lambda x: x['created'], reverse=True)
            
            return charges
            
        except stripe.error.InvalidRequestError as e:
            messages.error(request, f"Invalid request: {str(e)}")
            print(f"Stripe error (Invalid Request): {str(e)}")
            return []
        except stripe.error.AuthenticationError as e:
            messages.error(request, f"Authentication error: {str(e)}")
            print(f"Stripe error (Authentication): {str(e)}")
            return []
        except stripe.error.APIConnectionError as e:
            messages.error(request, f"API connection error: {str(e)}")
            print(f"Stripe error (API Connection): {str(e)}")
            return []
        except stripe.error.StripeError as e:
            messages.error(request, f"Payment processing error: {str(e)}")
            print(f"Stripe error: {str(e)}")
            return []
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {str(e)}")
            print(f"Unexpected error: {str(e)}")
            return []
    
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
        
    def getStripeOnboardingLink(request, accountId, domain, finalLink):
        try:
            account_links = stripe.AccountLink.create(
                account=accountId,
                refresh_url=f'{domain}/refresh/{accountId}',
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

    def getStripeAccountLogin(request, user):
        try:
            account = stripe.Account.retrieve(user.connectAccountID)

            if not account.details_submitted:
                return None

            account_link = stripe.Account.create_login_link(user.connectAccountID)
            return account_link.url

        except stripe.error.StripeError as e:
            messages.error(request, f"Stripe error: {e.user_message}")
            return JsonResponse({"error": e.user_message})
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return JsonResponse({"error": str(e)})
