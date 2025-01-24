from datetime import datetime
import time
import json
import stripe
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail
import stripe.error
from wave_v1.decorators import check_suspension, host, member, verified, onboarded
from django.urls import reverse


from accountManagementApp.models import UserProfile
from collegeManagementApp.models import (
    Organization,
    OrganizationMembership,
    CollegeEventLink,
)
from .forms import HostApplicationForm, EventForm, EditEventForm
from stripeManagementApp.getRequiredActions import getRequiredActions
from stripeManagementApp.updateConnectWithStripeDetails import (
    updateConnectWithStripeDetails,
)
from stripeManagementApp.createHostProduct import createHostProduct
from stripeManagementApp.createHostProductPrice import createProductPriceType
from stripeManagementApp.getEarnings import GetEarnings
from stripeManagementApp.processCashout import CashoutRequest
from stripeManagementApp.createExternalAccount import ExternalAccounts
from stripeManagementApp.getHostTransactions import Transactions


from eventTicketsApp.forms import InvitationForm, PaidFreeTicketForm
from .models import EventType, HostApplication, Event, EventPrivacy, HostProfile
from authenticationApp.models import CustomUser

from eventTicketsApp.models import InviteEventOption, RSVPTicket, PaidFreeTicket, Ticket


# Create your views here.
def hostView(request):
    pageName = "Host Event"
    return render(
        request, "eventManagementApp/host/hostHome.html", {"pageName": pageName}
    )


@login_required
@host
@check_suspension
def hostPortalView(request):
    live_event = Event.objects.filter(host=request.user, status="live")
    incomplete_event = Event.objects.filter(host=request.user, status="incomplete")

    user_profile = UserProfile.objects.get(user=request.user)
    is_in_college = user_profile.college is not None

    if request.method == "POST":
        action = request.POST.get("eventAction")
        event_id = request.POST.get("event_id")

        if action == "deleteEvent" and event_id:
            event_to_delete = get_object_or_404(
                Event, eventId=event_id, host=request.user
            )
            event_to_delete.delete()
            return redirect("eventManagement:hostPortal")

        if "displayOnCollege" in request.POST:
            event_to_update = get_object_or_404(
                Event, eventId=event_id, host=request.user
            )
            event_to_update.display_event_on_college = (
                request.POST["displayOnCollege"] == "True"
            )  # Check for 'true'
            event_to_update.save()
            return redirect("eventManagement:hostPortal")
    return render(
        request,
        "eventManagementApp/host/hostPortal.html",
        {
            "liveEvents": live_event,
            "incompleteEvents": incomplete_event,
            "isInCollege": is_in_college,
        },
    )


def hostGuideView(request):
    return render(request, "eventManagementApp/host/hostGuide.html")


@login_required
@member
@check_suspension
def eventCreationProcess(request):
    event_type_choices = Event.EVENT_TYPE_CHOICES
    privacy_choices = Event.PRIVACY_CHOICES
    placesKey = settings.PLACES_API_KEY
    
    userAccount = get_object_or_404(CustomUser, username=request.user.username)
    
    if not userAccount.groups.filter(name="Host").exists():
        hostRole, _ = Group.objects.get_or_create(name="Host")
        userAccount.groups.add(hostRole)

    if request.method == "POST":
        eventForm = EventForm(request.POST, request.FILES)
        go_live = request.POST.get("goLiveInput") == "1"

        if eventForm.is_valid():
            event = eventForm.save()
            event.event_type = request.POST.get("event_type")

            if go_live:
                crew_discount = request.POST.get('crew_discount')
                if crew_discount == "on":
                    event.crew_discount = True
                else:
                    event.crew_discount = False
                event_status = "live"
                event.status = event_status
                
                messages.success(request, "Event is live!")

                user_profile = event.host.user_profile
                hostProfile = HostProfile.objects.get(user=request.user)
                organization_membership = OrganizationMembership.objects.filter(
                    user=event.host
                ).first()

                if event.privacy == "Discoverable":
                    event_privacy = EventPrivacy.objects.create(
                        event=event,
                        display_on_explore=True,
                        require_invitation=False,
                        restricted_college=None,
                        restricted_organization=None,
                    )
                    event_privacy.save()

                elif event.privacy == "Invite Only":
                    event_privacy = EventPrivacy.objects.create(
                        event=event,
                        display_on_explore=False,
                        require_invitation=True,
                        restricted_college=None,
                        restricted_organization=None,
                    )
                    event.ticketing = "Invite Required"
                    event_privacy.save()

                elif event.privacy == "Private (College)":
                    if not user_profile.college:
                        messages.error(
                            request,
                            "You must be a part of a college to create a college event.",
                        )
                        return redirect(
                            "eventManagement:eventManagement", eventId=event.eventId
                        )
                    else:
                        event_privacy = EventPrivacy.objects.create(
                            event=event,
                            display_on_explore=False,
                            require_invitation=False,
                            restricted_college=event.host.user_profile.college,
                            restricted_organization=None,
                        )
                        event.display_event_on_college = True
                        event_privacy.save()
                        if user_profile.college:
                            college_event_link = CollegeEventLink.objects.get_or_create(
                                college=user_profile.college, event=event
                            )

                elif (
                    event.privacy == "Private (Organization)"
                    and organization_membership
                ):
                    event_privacy = EventPrivacy.objects.create(
                        event=event,
                        display_on_explore=False,
                        require_invitation=False,
                        restricted_college=None,
                        restricted_organization=organization_membership.organization,
                    )
                    event_privacy.save()

                event.save()
                product = createHostProduct(event, hostProfile.stripe_account_id)

                if product is not None:
                    productId = product.id
                    event.stripeProductId = productId
                    print("Product ID:", productId)
                    event.save()
                else:
                    print("Product creation failed")
                    messages.error(request, "Product creation failed")
                    return redirect("eventManagement:eventManagement", eventId=event.eventId)

            else:
                event.save()

            return redirect("eventManagement:eventManagement", eventId=event.eventId)
    else:
        eventForm = EventForm()

    return render(
        request,
        "eventManagementApp/host/eventCreationProcess.html",
        {
            # "event": event,
            "eventForm": eventForm,
            "eventTypeChoices": event_type_choices,
            "privacyChoices": privacy_choices,
            "placesKey": placesKey,
        },
    )


@login_required
@host
@member
@check_suspension
def eventManagement(request, eventId):
    event = get_object_or_404(Event, eventId=eventId)
    user_profile = UserProfile.objects.get(user=request.user)
    hostProfile = HostProfile.objects.get(user=event.host)
    is_in_college = user_profile.college is not None
    event_privacy = EventPrivacy.objects.get(event=event)
    rsvp_list = RSVPTicket.objects.filter(event=event)
    paid_free_tickets = PaidFreeTicket.objects.filter(event=event)

    if request.method == "POST":
        action = request.POST.get("eventAction")

        if action == "deleteEvent":
            event.delete()
            return redirect("eventManagement:hostPortal")

        elif action == "removefromRSVPlist":
            rsvp_id = request.POST.get("rsvp_id")
            rsvp = get_object_or_404(RSVPTicket, ticket_id=rsvp_id)
            ticket = get_object_or_404(Ticket, guestEmail=rsvp.email, event=event)
            rsvp.delete()
            ticket.delete()
            return redirect("eventManagement:eventManagement", eventId=eventId)

        elif "displayOnCollege" in request.POST:
            event_to_update = get_object_or_404(
                Event, eventId=event.eventId, host=request.user
            )
            event_to_update.display_event_on_college = (
                request.POST["displayOnCollege"] == "True"
            )
            event_to_update.save()
            return redirect("eventManagement:eventManagement", eventId=eventId)

        elif action == "sendInvites":
            invitationForm = InvitationForm(request.POST)
            if invitationForm.is_valid():
                emails = invitationForm.cleaned_data["invite_emails"]
                subject = invitationForm.cleaned_data["invite_subject"]
                message = invitationForm.cleaned_data["invite_message"]
                emailList = [email.strip() for email in emails.split(",")]

                for email in emailList:
                    invitation = InviteEventOption.objects.create(
                        event=event, email=email
                    )
                    user_profile.invited_events.add(event)
                    user_profile.invitations.add(invitation)

                    invitation.save()

                    invitation_link = request.build_absolute_uri(
                        reverse(
                            "core:eventDetails_withToken",
                            kwargs={
                                "eventId": str(eventId),
                                "token": invitation.token,
                            },
                        )
                    )
                    emailMessageHtml = render_to_string(
                        "emailTemplates/eventManagementApp/host/inviteAttendees.html",
                        {"body": message, "invitationLink": invitation_link},
                    )
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=None,
                        fail_silently=False,
                        recipient_list=[email],
                        html_message=emailMessageHtml,
                    )
            return redirect("eventManagement:eventManagement", eventId=eventId)

        elif action == "saveChanges":
            editEventForm = EditEventForm(request.POST, request.FILES, instance=event)
            if editEventForm.is_valid():
                # Handle removing body photos if checked
                if "remove_body_photo_one" in request.POST:
                    event.body_photo_one.delete(save=False)
                    event.body_photo_one = None
                if "remove_body_photo_two" in request.POST:
                    event.body_photo_two.delete(save=False)
                    event.body_photo_two = None
                if "remove_body_photo_three" in request.POST:
                    event.body_photo_three.delete(save=False)
                    event.body_photo_three = None
                if "remove_body_photo_four" in request.POST:
                    event.body_photo_four.delete(save=False)
                    event.body_photo_four = None
                if "remove_body_photo_five" in request.POST:
                    event.body_photo_five.delete(save=False)
                    event.body_photo_five = None

                edits = editEventForm.save(commit=False)

                if "headerPhoto" in request.FILES:
                    edits.header_photo = request.FILES["headerPhoto"]
                if "bodyPhotoOne" in request.FILES:
                    edits.body_photo_one = request.FILES["bodyPhotoOne"]
                if "bodyPhotoTwo" in request.FILES:
                    edits.body_photo_two = request.FILES["bodyPhotoTwo"]
                if "bodyPhotoThree" in request.FILES:
                    edits.body_photo_three = request.FILES["bodyPhotoThree"]
                if "bodyPhotoFour" in request.FILES:
                    edits.body_photo_four = request.FILES["bodyPhotoFour"]
                if "bodyPhotoFive" in request.FILES:
                    edits.body_photo_five = request.FILES["bodyPhotoFive"]

                # >>>>>> HERE IS THE KEY LINE: <<<<<<
                # Capture the new 'age_restriction' from POST and save it:
                edits.age_restriction = request.POST.get("age_restriction", "")

                edits.save()
            else:
                print(editEventForm.errors)
            return redirect("eventManagement:eventManagement", eventId=eventId)

        elif action == "createPaidFreeTicket":
            paidFreeForm = PaidFreeTicketForm(request.POST)
            if paidFreeForm.is_valid():
                new_ticket = paidFreeForm.save(commit=False)
                new_ticket.event = event
                new_ticket.save()
                eventStripeId = event.stripeProductId
                print("Event Stripe ID:", eventStripeId)
                stripePrice = createProductPriceType(
                    eventStripeId,
                    new_ticket.ticket_price,
                    hostProfile.stripe_account_id,
                    new_ticket.ticket_quantity,
                )
                new_ticket.stripePriceId = stripePrice.id
                new_ticket.save()
                
            

            return redirect("eventManagement:eventManagement", eventId=eventId)

    else:
        invitationForm = InvitationForm()
        paidFreeForm = PaidFreeTicketForm()
        editEventForm = EditEventForm(instance=event)

    return render(
        request,
        "eventManagementApp/host/eventManagement.html",
        {
            "event": event,
            "isInCollege": is_in_college,
            "userProfile": user_profile,
            "eventPrivacy": event_privacy,
            "invitationForm": invitationForm,
            "rsvpList": rsvp_list,
            "paidFreeForm": paidFreeForm,
            "paidFreeTickets": paid_free_tickets,
            "editEventForm": editEventForm,
        },
    )


@login_required
@host
@member
@check_suspension
def hostBilling(request):
    hostProfile = HostProfile.objects.get(user=request.user)

    required_actions = []
    stripeKey = settings.STRIPE_PUBLISHABLE_KEY

    # Getting the required actions for the connected stripe account so that the stripe account is fully activated
    if hostProfile.stripe_account_id:
        stripeAccountBalance = GetEarnings.getStripeAccountBalance(
            hostProfile.stripe_account_id
        )

        totalEarnings = GetEarnings.getTotalEarnings(hostProfile.stripe_account_id)

        response = getRequiredActions(hostProfile.stripe_account_id)

        if response["status"] == "success":
            required_actions = response["required_actions"]
            print(f"All required actions: {required_actions}")
        else:
            messages.error(request, f"Error: {response['message']}")

    if request.method == "POST":
        action = request.POST.get("billingAction")

        if action == "removeBankAccount":
            hostStripeAccountId = hostProfile.stripe_account_id

            if not hostStripeAccountId:
                messages.error(request, "Stripe account not found.")
                return redirect("eventManagement:hostPortal")

            external_account_id = request.POST.get("externalBankAccountID")
            print(f"External account ID: {external_account_id}")

            if not external_account_id:
                messages.error(request, "Invalid request.")
                return redirect("eventManagement:hostBilling")

            ExternalAccounts.removePayoutMethod(
                request, hostStripeAccountId, external_account_id
            )

            messages.success(request, "Bank account removed successfully.")
            return redirect("eventManagement:hostBilling")

        elif action == "removeCardMethod":
            hostStripeAccountId = hostProfile.stripe_account_id

            if not hostStripeAccountId:
                messages.error(request, "Stripe account not found.")
                return redirect("eventManagement:hostPortal")

            external_account_id = request.POST.get("externalCardAccountID")
            print(f"External account ID: {external_account_id}")

            if not external_account_id:
                messages.error(request, "Invalid request.")
                return redirect("eventManagement:hostBilling")

            ExternalAccounts.removePayoutMethod(
                request, hostStripeAccountId, external_account_id
            )

            messages.success(request, "Bank account removed successfully.")
            return redirect("eventManagement:hostBilling")

        elif action == "addBankAccountNew":
            hostStripeAccountId = hostProfile.stripe_account_id

            if not hostStripeAccountId:
                messages.error(request, "Stripe account not found.")
                return redirect("eventManagement:hostPortal")

            account_holder_name = request.POST.get("accountHolderName")
            bank_account_number = request.POST.get("accountNumber")
            routing_number = request.POST.get("accountRoutingNumber")

            if not account_holder_name or not bank_account_number or not routing_number:
                messages.error(request, "Please fill in all required fields.")
                return redirect("eventManagement:hostBilling")

            value = ExternalAccounts.createBankAccount(
                request,
                hostStripeAccountId,
                account_holder_name,
                bank_account_number,
                routing_number,
            )

        elif action == "setBankDefaultPaymentMethod":
            hostStripeAccountId = hostProfile.stripe_account_id

            if not hostStripeAccountId:
                messages.error(request, "Stripe account not found.")
                return redirect("eventManagement:hostPortal")

            external_account_id = request.POST.get("setBankDefaultAccountID")

            if not external_account_id:
                messages.error(request, "Invalid request.")
                return redirect("eventManagement:hostBilling")

            changed = ExternalAccounts.setDefaultPaymentMethod(
                request, hostStripeAccountId, external_account_id
            )

            if changed:
                print("Default payment method set successfully.")
                messages.success(request, "Default payment method set successfully.")

        elif action == "setCardDefaultPaymentMethod":
            hostStripeAccountId = hostProfile.stripe_account_id

            if not hostStripeAccountId:
                messages.error(request, "Stripe account not found.")
                return redirect("eventManagement:hostPortal")

            external_account_id = request.POST.get("setCardDefaultAccountID")

            if not external_account_id:
                messages.error(request, "Invalid request.")
                return redirect("eventManagement:hostBilling")

            changed = ExternalAccounts.setDefaultPaymentMethod(
                request, hostStripeAccountId, external_account_id
            )

            if changed:
                print("Default payment method set successfully.")
                messages.success(request, "Default payment method set successfully.")

        elif action == "completeRequiredActions":
            print(request.POST)
            update_data = {}
            if (
                "business_profile" in required_actions
                or "business_profile.url" in required_actions
                or "business_profile.name" in required_actions
                or "business_profile.support_phone" in required_actions
                or "business_profile.support_email" in required_actions
                or "business_profile.support_url" in required_actions
                or "business_profile.support_address" in required_actions
                or "business_profile.product_description" in required_actions
            ):
                update_data["business_profile.url"] = request.POST.get(
                    "businessProfileURL"
                )
                update_data["business_profile.business_name"] = request.POST.get(
                    "businessName"
                )
                update_data["business_profile.support_email"] = request.POST.get(
                    "supportEmail"
                )
                update_data["business_profile.support_phone"] = request.POST.get(
                    "supportPhone"
                )
                update_data["business_profile.support_url"] = request.POST.get(
                    "businessProfileURL"
                )
                update_data["business_profile.product_description"] = request.POST.get(
                    "businessProductDescription"
                )
                update_data["business_profile.support_address"] = {
                    "line1": request.POST.get("street"),
                    "city": request.POST.get("city"),
                    "state": request.POST.get("state"),
                    "postal_code": request.POST.get("postalCode"),
                    "country": request.POST.get("country"),
                }

            if "external_account" in required_actions:
                update_data["bank_details"] = {
                    "account_holder_name": request.POST.get("accountHolderName"),
                    "account_number": request.POST.get("accountNumber"),
                    "routing_number": request.POST.get("accountRoutingNumber"),
                }

            if (
                "individual.first_name" in required_actions
                or "individual.last_name" in required_actions
            ):
                update_data["individual.first_name"] = request.POST.get("firstName")
                update_data["individual.last_name"] = request.POST.get("lastName")

            if (
                "individual.dob.day" in required_actions
                or "individual.dob.month" in required_actions
                or "individual.dob.year" in required_actions
            ):
                update_data["individual.dob.day"] = request.POST.get("dobDay")
                update_data["individual.dob.month"] = request.POST.get("dobMonth")
                update_data["individual.dob.year"] = request.POST.get("dobYear")

            if (
                "individual.ssn_last_4" in required_actions
                or "ssn_last_4" in required_actions
            ):
                update_data["ssn_last_4"] = request.POST.get("ssn")

            if "individual" in required_actions:
                update_data["address"] = {
                    "line1": request.POST.get("street"),
                    "city": request.POST.get("city"),
                    "state": request.POST.get("state"),
                    "postal_code": request.POST.get("postalCode"),
                    "country": request.POST.get("country"),
                }

            if (
                "tos_acceptance" in required_actions
                or "tos_acceptance.ip" in required_actions
            ):
                update_data["tos_acceptance"] = {
                    "date": int(time.time()),
                    "ip": get_client_ip(request),
                    "user_agent": request.META.get("HTTP_USER_AGENT"),
                    "service_agreement": "full",
                }

            print(update_data)
            # Send updates to Stripe
            response = updateConnectWithStripeDetails(hostProfile, update_data)
            if response["status"] == "success":
                messages.success(request, "Required actions completed successfully.")
            else:
                print(f"Error: {response['message']}")
                messages.error(request, f"Error: {response['message']}")

            return redirect("eventManagement:hostBilling")

        elif action == "refundTransaction":
            hostStripeAccountId = hostProfile.stripe_account_id

            if not hostStripeAccountId:
                messages.error(request, "Stripe account not found.")
                return redirect("eventManagement:hostPortal")

            refund_transaction_id = request.POST.get("refundTransactionID")
            print(f"Refund transaction ID: {refund_transaction_id}")
            if not refund_transaction_id:
                print("Invalid transaction ID provided.")
                messages.error(request, "Invalid transaction ID provided.")
                return redirect("eventManagement:hostBilling")

            if hostStripeAccountId and refund_transaction_id:
                Transactions.processRefund(
                    request, hostStripeAccountId, refund_transaction_id
                )

    connectedAccount = hostProfile.stripe_account_id
    external_accounts = {"bank_accounts": [], "cards": []}

    if connectedAccount:
        try:
            external_accounts = stripe.Account.list_external_accounts(
                connectedAccount,
            )

            external_accounts["bank_accounts"] = [
                account
                for account in external_accounts.data
                if account.object == "bank_account"
            ]
            external_accounts["cards"] = [
                account
                for account in external_accounts.data
                if account.object == "card"
            ]
            # print(external_accounts)
        except stripe.error.StripeError as e:
            messages.error(request, f"Error: {e.user_message}")
            return redirect("eventManagement:hostPortal")

    transactions = Transactions.getHostTransactions(request, connectedAccount)

    payouts = Transactions.getHostPayouts(request, connectedAccount) or {}

    return render(
        request,
        "eventManagementApp/billing/hostBilling.html",
        {
            "hostProfile": hostProfile,
            "requiredActions": required_actions,
            "stripeAccountBalance": stripeAccountBalance,
            "totalEarnings": totalEarnings,
            "externalAccounts": external_accounts,
            "stripeKey": stripeKey,
            "transactions": transactions,
            "payouts": payouts,
        },
    )


def addCard(request):
    print("addCard view reached!")  # Debug print
    try:
        if not request.body:
            return JsonResponse({"error": "No data provided"}, status=400)

        data = json.loads(request.body)
        token = data.get("token")

        if not token:
            return JsonResponse({"error": "No token provided"}, status=400)

        hostProfile = HostProfile.objects.get(user=request.user)
        hostStripeAccountId = hostProfile.stripe_account_id

        ExternalAccounts.createCard(hostStripeAccountId, token)
        return redirect("eventManagement:hostBilling")

    except Exception as e:
        print(f"Error in addCard view: {str(e)}")  # Debug print
        return JsonResponse({"error": str(e)}, status=500)


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


@login_required
@host
@member
@check_suspension
def hostBillingCashout(request):
    hostProfile = HostProfile.objects.get(user=request.user)
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            amount = data.get("amount")
            print(f"Received amount: {amount}")

            if not amount or float(amount) <= 0:
                return JsonResponse(
                    {"sucess": False, "error": "Invalid amount"}, status=400
                )

            amount_in_cents = int(float(amount) * 100)

            # external_accountId = CashoutRequest.getExternalAccountId(hostProfile.stripe_account_id)
            CashoutRequest.processCashoutRequest(
                amount_in_cents, "usd", hostProfile.stripe_account_id
            )

            return JsonResponse(
                {"success": True, "message": "Cashout request successful!"}
            )
        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse(
                {"success": False, "error": "An error occurred"}, status=400
            )
    return JsonResponse({"success": False, "error": "Invalid request"}, status=405)


@login_required
@host
@member
@check_suspension
def hostAnalyticsHome(request):
    hostLiveEvents = Event.objects.filter(host=request.user, status="live")
    return render(
        request,
        "eventManagementApp/host/analytics/analyticsHome.html",
        {"hostLiveEvents": hostLiveEvents},
    )


@login_required
@host
@member
@check_suspension
def hostEventAnalytics(request, eventId):
    event = get_object_or_404(Event, eventId=eventId)
    return render(
        request,
        "eventManagementApp/host/analytics/event/event.html",
        {"event": event},
    )