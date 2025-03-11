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
from django.views.decorators.csrf import csrf_exempt


from accountManagementApp.models import UserProfile
from collegeManagementApp.models import Organization, OrganizationMembership
from .forms import CouponCodeForm, HostApplicationForm, EventForm, EditEventForm
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
from .models import EventType, HostApplication, Event, HostProfile, CouponCode
from authenticationApp.models import CustomUser

from eventTicketsApp.models import InviteEventOption, RSVPTicket, PaidFreeTicket, Ticket
from stripeManagementApp.customerSetup import ConnectAccount


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
            
        # Handle the college display form submission
        if "displayOnCollegeValue" in request.POST and event_id:
            event_to_update = get_object_or_404(
                Event, eventId=event_id, host=request.user
            )
            event_to_update.display_event_on_college = (
                request.POST["displayOnCollegeValue"] == "True"
            )
            event_to_update.save()
            return redirect("eventManagement:hostPortal")

    # After handling POST requests
    context = {
        "liveEvents": live_event,
        "incompleteEvents": incomplete_event,
        "isInCollege": is_in_college,
    }
    return render(request, "eventManagementApp/host/hostPortal.html", context)


def hostGuideView(request):
    return render(request, "eventManagementApp/host/hostGuide.html")


@login_required
@member
@verified
@verified
@check_suspension
def eventCreationSelect(request):
    siteDomain = settings.SITE_URL
    userAccount = get_object_or_404(CustomUser, username=request.user.username)
    completedConnectAccount = False

    siteDomain = settings.SITE_URL
    link = request.build_absolute_uri(reverse("eventManagement:eventCreationSelect"))

    # Path 1: If no connectAccountID, search Stripe for an account by email
    if not userAccount.connectAccountID:
        # Search for existing accounts using list instead of search
        stripe_accounts = stripe.Account.list(limit=1)
        existing_account = None
        
        # Look for account with matching email
        for account in stripe_accounts.data:
            if account.get('email') == userAccount.email:
                existing_account = account
                break

        if existing_account:
            # Delete old account if found
            stripe.Account.delete(existing_account.id)

        # Path 1.1: Create a new Stripe Connect account
        stripeConnectAccount = ConnectAccount.createConnectAccount(request, userAccount)
        if stripeConnectAccount:
            userAccount.connectAccountID = stripeConnectAccount.id
            userAccount.connectAccountCreated = True
            userAccount.save()
            completedConnectAccount = True

    # Path 2: Now that we have a Connect account ID, generate the onboarding link
    if userAccount.connectAccountID:
        try:
            stripeLinkAccount = ConnectAccount.getStripeOnboardingLink(
                request, userAccount.connectAccountID, siteDomain, link
            )
        except stripe.error.StripeError as e:
            messages.error(request, f"Failed to generate onboarding link: {str(e)}")
            stripeLinkAccount = None
    else:
        stripeLinkAccount = None

    # Assign "Host" role if not already assigned
    if not userAccount.groups.filter(name="Host").exists():
        hostRole, _ = Group.objects.get_or_create(name="Host")
        userAccount.groups.add(hostRole)

    if request.method == "POST":
        eventAction = request.POST.get("eventAction")

        if eventAction == "paid":
            try:
                stripeConnectAccount = stripe.Account.retrieve(userAccount.connectAccountID)
                if stripeConnectAccount.get("payouts_enabled"):
                    completedConnectAccount = True

                time.sleep(2)

                if not completedConnectAccount:
                    messages.error(request, "Please complete your Stripe account setup.")
                    return redirect(stripeLinkAccount)
                return redirect("eventManagement:createPaidEvent")
            except stripe.error.StripeError as e:
                messages.error(request, f"Stripe account verification failed: {str(e)}")
                return redirect("eventManagement:eventCreationSelect")
                
        if eventAction == "free":
            return redirect("eventManagement:createFreeEvent")

    return render(request, "eventManagementApp/host/eventCreationSelect.html")


@login_required
@member
@verified
@check_suspension
def createPaidEvent(request):
    event_type_choices = Event.EVENT_TYPE_CHOICES
    placesKey = settings.PLACES_API_KEY

    userAccount = get_object_or_404(CustomUser, username=request.user.username)

    if request.method == "POST":
        eventForm = EventForm(request.POST, request.FILES, user=request.user)
        eventAction = request.POST.get("eventAction")

        if eventAction == "submit" and eventForm.is_valid():
            event = eventForm.save(commit=False)
            event.host = userAccount
            event.ticketing = "Paid"
            event.crew_discount = request.POST.get("crew_discount") == "on"
            event.show_guest_list = request.POST.get("show_guest_list") == "on"
            event.forAllDisplay = request.POST.get("forAllDisplay") == "on"
            event.forCollegesDisplay = request.POST.get("forCollegesDisplay") == "on"
            event.status = "live"
            
            # Save the event
            event.save()

            # Ensure host profile exists
            hostProfile, _ = HostProfile.objects.get_or_create(user=request.user)

            # Create Stripe product
            product = createHostProduct(event, hostProfile.stripe_account_id)

            if product:
                event.stripeProductId = product.id
                event.save()
                messages.success(request, "Event is live!")
                return redirect("eventManagement:paidTicketing", eventId=event.eventId)
            else:
                print(f"Product creation failed for event ID {event.eventId}")
                messages.error(request, "Stripe product creation failed. Please try again.")
                event.delete()
                return redirect("eventManagement:hostHome")

        else:
            print("Invalid event form submission:", eventForm.errors)
            messages.error(request, "Invalid form submission.")

    else:
        eventForm = EventForm(user=request.user)

    return render(
        request,
        "eventManagementApp/host/create/createPaidEvent.html",
        {
            "eventForm": eventForm,
            "eventTypeChoices": event_type_choices,
            "placesKey": placesKey,
        },
    )


@login_required
@member
@verified
@check_suspension
def createFreeEvent(request):
    event_type_choices = Event.EVENT_TYPE_CHOICES
    placesKey = settings.PLACES_API_KEY

    userAccount = get_object_or_404(CustomUser, username=request.user.username)

    if request.method == "POST":
        eventForm = EventForm(request.POST, request.FILES, user=request.user)
        eventAction = request.POST.get("eventAction")

        if eventAction == "submit":
            if eventForm.is_valid():
                event = eventForm.save(commit=False)
                event.host = userAccount
                event.ticketing = "Free"
                event.crew_discount = False
                event.show_guest_list = request.POST.get("show_guest_list") == "on"
                event.forAllDisplay = request.POST.get("forAllDisplay") == "on"
                event.forCollegesDisplay = request.POST.get("forCollegesDisplay") == "on"
                event.status = "live"

                event.save()

                messages.success(request, "Event is live!")

                hostProfile, _ = HostProfile.objects.get_or_create(user=request.user)                

                return redirect(
                    "eventManagement:eventManagement", eventId=event.eventId
                )

            else:
                messages.error(request, "Invalid form submission.")

    else:
        eventForm = EventForm(user=request.user)

    return render(
        request,
        "eventManagementApp/host/create/createFreeEvent.html",
        {
            "eventForm": eventForm,
            "eventTypeChoices": event_type_choices,
            "placesKey": placesKey,
        },
    )

@login_required
@member
@verified
@check_suspension
def createPaidEventTicket(request, eventId):
    event = get_object_or_404(Event, eventId=eventId)
    hostProfile = HostProfile.objects.get(user=event.host)
    try:
        paidFreeForm = PaidFreeTicketForm(request.POST)
        paid_free_tickets = PaidFreeTicket.objects.filter(event=event)
        couponCodeForm = CouponCodeForm(request.POST)
        coupon_codes = CouponCode.objects.filter(event=event)
    except Exception as e:
        print(f"Error in createPaidEventTicket: {str(e)}")
        messages.error(request, "An error occurred. Please try again.")
        return redirect("eventManagement:hostHome")

    eventAction = request.POST.get("eventAction")
    ticket_id = request.POST.get("ticketId")

    if request.method == "POST":
        if eventAction == "createPaidFreeTicket":
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

                return redirect("eventManagement:paidTicketing", eventId=event.eventId)
            else:
                messages.error(request, "Invalid form submission.")
                return redirect(
                    "eventManagement:paidTicketing", eventId=event.eventId
                )
        elif eventAction == "deleteTicket":
            ticket = get_object_or_404(PaidFreeTicket, ticket_id=ticket_id)
            ticket.delete()
            return redirect(
                "eventManagement:paidTicketing", eventId=event.eventId
            )
        elif eventAction == "editTicket":
            return redirect("eventManagement:eventManagement", eventId=event.eventId)
        elif eventAction == "createCouponCode":
            if couponCodeForm.is_valid():
                new_coupon = couponCodeForm.save(commit=False)
                new_coupon.event = event
                new_coupon.save()
                return redirect("eventManagement:paidTicketing", eventId=event.eventId)
            else:
                messages.error(request, "Invalid form submission.")
                return redirect("eventManagement:paidTicketing", eventId=event.eventId)
        elif eventAction == "deleteCouponCode":
            coupon_id = request.POST.get("couponId")
            coupon = get_object_or_404(CouponCode, coupon_id=coupon_id)
            coupon.delete()
            return redirect("eventManagement:paidTicketing", eventId=event.eventId)
            

    return render(
        request,
        "eventManagementApp/ticketing/createPaidEventTicket.html",
        {
            "paidFreeForm": paidFreeForm,
            "paidFreeTickets": paid_free_tickets,
            "event": event,
            "couponCodesForm": couponCodeForm,
            "couponCodes": coupon_codes,
        },
    )


def createInviteEventTicket(request, event):
    eventId = event.eventId
    invitationForm = InvitationForm(request.POST)
    user_profile = UserProfile.objects.get(user=request.user)
    hostProfile = HostProfile.objects.get(user=event.host)

    if request.method == "POST":
        if invitationForm.is_valid():
            emails = invitationForm.cleaned_data["invite_emails"]
            subject = invitationForm.cleaned_data["invite_subject"]
            message = invitationForm.cleaned_data["invite_message"]
            emailList = [email.strip() for email in emails.split(",")]

            for email in emailList:
                invitation = InviteEventOption.objects.create(event=event, email=email)
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
    return render(
        request,
        "eventManagementApp/ticketing/createInviteEventTicket.html",
        {"invitationForm": invitationForm},
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
    rsvp_list = RSVPTicket.objects.filter(event=event)
    paid_free_tickets = PaidFreeTicket.objects.filter(event=event)

    if request.method == "POST":
        action = request.POST.get("eventAction")
        ticket_id = request.POST.get("ticketId")

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

        elif action == "deleteTicket":
            ticket = get_object_or_404(PaidFreeTicket, ticket_id=ticket_id)
            ticket.delete()
            return redirect("eventManagement:eventManagement", eventId=eventId)

        elif action == "saveTicketEdit":
            ticket = get_object_or_404(PaidFreeTicket, ticket_id=ticket_id)
            paidFreeForm = PaidFreeTicketForm(request.POST, instance=ticket)
            if paidFreeForm.is_valid():
                ticket = paidFreeForm.save(commit=False)
                ticket.save()
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

        elif action == "editEvent":
            return redirect("eventManagement:editEvent", eventId=eventId)

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
            event.hide_address = "hide_address" in request.POST
            print(request.POST.get("hide_address"))
            event.save()
            messages.success(request, "Address is now hidden" if event.hide_address else "Address is now visible")
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
            "rsvpList": rsvp_list,
            "paidFreeForm": paidFreeForm,
            "paidFreeTickets": paid_free_tickets,
            "editEventForm": editEventForm,
        },
    )


def editEvent(request, eventId):
    event = get_object_or_404(Event, eventId=eventId)
    user_profile = UserProfile.objects.get(user=request.user)
    hostProfile = HostProfile.objects.get(user=event.host)
    is_in_college = user_profile.college is not None
    rsvp_list = RSVPTicket.objects.filter(event=event)
    paid_free_tickets = PaidFreeTicket.objects.filter(event=event)

    if request.method == "POST":
        editEventForm = EditEventForm(request.POST, request.FILES, instance=event)
        if editEventForm.is_valid():
            editEventForm.save()
            messages.success(request, "Event updated successfully.")
        else:
            for field, errors in editEventForm.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")
        return redirect("eventManagement:eventManagement", eventId=eventId)
    else:
        editEventForm = EditEventForm(instance=event)

    return render(
        request,
        "eventManagementApp/host/editEvent.html",
        {
            "event": event,
            "isInCollege": is_in_college,
            "userProfile": user_profile,
            "rsvpList": rsvp_list,
            "paidFreeTickets": paid_free_tickets,
            "editEventForm": editEventForm,
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
