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
from collegeManagementApp.models import (
    Organization,
    OrganizationMembership
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
from .utils import set_event_privacy  # Import the helper function

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
@verified
@onboarded
@check_suspension
def eventCreationSelect(request):
    siteDomain = settings.SITE_URL
    userAccount = get_object_or_404(CustomUser, username=request.user.username)
       
    
    connectAccountExists = userAccount.connectAccountCreated
    connectOnboarded = userAccount.connectAccountOnboarded
    
    if connectAccountExists == True and connectOnboarded == True:
        completedConnectAccount = True
    else:
        completedConnectAccount = False
    
    if not userAccount.connectAccountID:
        stripeConnectAccount = ConnectAccount.createConnectAccount(request, userAccount)
        if stripeConnectAccount:
            userAccount.connectAccountID = stripeConnectAccount.id
            userAccount.connectAccountCreated = True
            userAccount.save()
            completedConnectAccount = True
    
    
    siteDomain = settings.SITE_URL
    
    link = request.build_absolute_uri(reverse("eventManagement:createPaidEvent"))
    
    
    stripeLinkAccount = ConnectAccount.getStripeOnboardingLink(request, userAccount, siteDomain, link)
    
    print("Stripe Link Account:", stripeLinkAccount)

    
    
    if not userAccount.groups.filter(name="Host").exists():
        hostRole, _ = Group.objects.get_or_create(name="Host")
        userAccount.groups.add(hostRole)
        
    if request.method == "POST":
        eventAction = request.POST.get("eventAction")
        
        if eventAction == "paid":
            if not completedConnectAccount:
                messages.error(request, "Please complete your Stripe account setup.")
                return redirect(stripeLinkAccount)
            return redirect("eventManagement:createPaidEvent")
        elif eventAction == "rsvp":
            return redirect("eventManagement:createRsvpEvent")
        elif eventAction == "invite":
            return redirect("eventManagement:createInviteEvent")
        
    return render(request, "eventManagementApp/host/eventCreationSelect.html")


@login_required
@member
@onboarded
@check_suspension
def createPaidEvent(request):
    event_type_choices = Event.EVENT_TYPE_CHOICES
    privacy_choices = Event.PRIVACY_CHOICES
    placesKey = settings.PLACES_API_KEY
    
    userAccount = get_object_or_404(CustomUser, username=request.user.username)
    
    if request.method == "POST":
        eventForm = EventForm(request.POST, request.FILES)
        eventAction = request.POST.get("eventAction")
        
        if eventAction == "submit":
            if eventForm.is_valid():      
                event = eventForm.save(commit=False)
                event.host = userAccount
                event.ticketing = "Invite Required"
                event.crew_discount = request.POST.get('crew_discount') == "on"
                event.show_guest_list = request.POST.get('show_guest_list') == "on"
                
                event.status = "live"
                
                event.save()

                messages.success(request, "Event is live!")

                user_profile = event.host.user_profile
                hostProfile, _ = HostProfile.objects.get_or_create(user=request.user)
                organization_membership = OrganizationMembership.objects.filter(
                    user=event.host
                ).first()
                
                # Refactored privacy setting
                privacy_set = set_event_privacy(event, user_profile, organization_membership, request)
                if not privacy_set:
                    return redirect("eventManagement:eventManagement", eventId=event.eventId)

                event.save()
                product = createHostProduct(event, hostProfile.stripe_account_id)

                if product:
                    event.stripeProductId = product.id
                    event.save()
                else:
                    print("Product creation failed")
                    print("Product creation failed")
                    print("Product creation failed")
                    messages.error(request, "Product creation failed")
                    return redirect("eventManagement:eventManagement", eventId=event.eventId)

                return redirect("eventManagement:eventManagement", eventId=event.eventId)
            
            else:
                print(eventForm.errors)
                print(eventForm.errors)
                print(eventForm.errors)
                messages.error(request, "Invalid form submission.")
                # Optionally, handle form errors here

    else:
        eventForm = EventForm()

    return render(
        request,
        "eventManagementApp/host/create/createInviteEvent.html",
        {
            "eventForm": eventForm,
            "eventTypeChoices": event_type_choices,
            "privacyChoices": privacy_choices,
            "placesKey": placesKey,
        },
    )


@login_required
@member
@onboarded
@check_suspension
def createInviteEvent(request):
    event_type_choices = Event.EVENT_TYPE_CHOICES
    privacy_choices = Event.PRIVACY_CHOICES
    placesKey = settings.PLACES_API_KEY
    
    userAccount = get_object_or_404(CustomUser, username=request.user.username)
    
    if request.method == "POST":
        eventForm = EventForm(request.POST, request.FILES)
        eventAction = request.POST.get("eventAction")
        
        if eventAction == "submit":
            if eventForm.is_valid():      
                event = eventForm.save(commit=False)
                event.host = userAccount
                event.ticketing = "Invite Required"
                event.crew_discount = request.POST.get('crew_discount') == "on"
                event.show_guest_list = request.POST.get('show_guest_list') == "on"
                
                event.status = "live"
                
                event.save()

                messages.success(request, "Event is live!")

                user_profile = event.host.user_profile
                hostProfile, _ = HostProfile.objects.get_or_create(user=request.user)
                organization_membership = OrganizationMembership.objects.filter(
                    user=event.host
                ).first()
                
                # Refactored privacy setting
                privacy_set = set_event_privacy(event, user_profile, organization_membership, request)
                if not privacy_set:
                    return redirect("eventManagement:eventManagement", eventId=event.eventId)

                event.save()
                product = createHostProduct(event, hostProfile.stripe_account_id)

                if product:
                    event.stripeProductId = product.id
                    event.save()
                else:
                    print("Product creation failed")
                    print("Product creation failed")
                    print("Product creation failed")
                    messages.error(request, "Product creation failed")
                    return redirect("eventManagement:eventManagement", eventId=event.eventId)

                return redirect("eventManagement:eventManagement", eventId=event.eventId)
            
            else:
                print(eventForm.errors)
                print(eventForm.errors)
                print(eventForm.errors)
                messages.error(request, "Invalid form submission.")
                # Optionally, handle form errors here

    else:
        eventForm = EventForm()

    return render(
        request,
        "eventManagementApp/host/create/createInviteEvent.html",
        {
            "eventForm": eventForm,
            "eventTypeChoices": event_type_choices,
            "privacyChoices": privacy_choices,
            "placesKey": placesKey,
        },
    )

@login_required
@member
@onboarded
@check_suspension
def createRsvpEvent(request):
    event_type_choices = Event.EVENT_TYPE_CHOICES
    privacy_choices = Event.PRIVACY_CHOICES
    placesKey = settings.PLACES_API_KEY
    
    userAccount = get_object_or_404(CustomUser, username=request.user.username)
    
    if request.method == "POST":
        eventForm = EventForm(request.POST, request.FILES)
        eventAction = request.POST.get("eventAction")
        
        if eventAction == "submit":
            if eventForm.is_valid():      
                event = eventForm.save(commit=False)
                event.host = userAccount
                event.ticketing = "RSVP Required"
                event.crew_discount = request.POST.get('crew_discount') == "on"
                event.show_guest_list = request.POST.get('show_guest_list') == "on"
                
                event.status = "live"
                
                event.save()

                messages.success(request, "Event is live!")

                user_profile = event.host.user_profile
                hostProfile, _ = HostProfile.objects.get_or_create(user=request.user)
                organization_membership = OrganizationMembership.objects.filter(
                    user=event.host
                ).first()
                
                # Refactored privacy setting
                privacy_set = set_event_privacy(event, user_profile, organization_membership, request)
                if not privacy_set:
                    return redirect("eventManagement:eventManagement", eventId=event.eventId)

                event.save()
                product = createHostProduct(event, hostProfile.stripe_account_id)

                if product:
                    event.stripeProductId = product.id
                    event.save()
                else:
                    print("Product creation failed")
                    print("Product creation failed")
                    print("Product creation failed")
                    messages.error(request, "Product creation failed")
                    return redirect("eventManagement:eventManagement", eventId=event.eventId)

                return redirect("eventManagement:eventManagement", eventId=event.eventId)
            
            else:
                print(eventForm.errors)
                print(eventForm.errors)
                print(eventForm.errors)
                messages.error(request, "Invalid form submission.")
                # Optionally, handle form errors here

    else:
        eventForm = EventForm()

    return render(
        request,
        "eventManagementApp/host/create/createRsvpEvent.html",
        {
            "eventForm": eventForm,
            "eventTypeChoices": event_type_choices,
            "privacyChoices": privacy_choices,
            "placesKey": placesKey,
        },
    )


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET_TES

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return JsonResponse({"error": "Invalid payload"}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({"error": "Invalid signature"}, status=400)

    if event["type"] == "account.updated":
        account = event["data"]["object"]
        user = CustomUser.objects.filter(connectAccountID=account["id"]).first()
        if user and account["details_submitted"]:
            user.connectAccountOnboarded = True
            user.save()

    return JsonResponse({"status": "success"}, status=200)
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