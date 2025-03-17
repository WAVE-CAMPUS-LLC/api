from datetime import datetime
import time
import json
import stripe
from django import forms
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime
import uuid
from wave_v1.decorators import host, check_suspension
from stripeManagementApp.createHostProduct import createHostProduct

from accountManagementApp.models import UserProfile
from collegeManagementApp.models import Organization, OrganizationMembership
from .forms import HostApplicationForm, EventForm, EditEventForm
from eventTicketsApp.models import InviteEventOption, RSVPTicket, PaidFreeTicket, Ticket
from eventTicketsApp.serializers import TicketSerializer
from .serializers import EventSerializer
from eventTicketsApp.forms import InvitationForm, PaidFreeTicketForm
from .models import EventType, HostApplication, Event, HostProfile
from authenticationApp.models import CustomUser
from stripeManagementApp.createHostProduct import createHostProduct


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def host_portal(request):
    if request.method == "GET":
        live_events = Event.objects.filter(host=request.user, status="live")
        incomplete_events = Event.objects.filter(host=request.user, status="incomplete")

        user_profile = get_object_or_404(UserProfile, user=request.user)
        is_in_college = user_profile.college is not None

        return Response(
            {
                "liveEvents": EventSerializer(live_events, many=True).data,
                "incompleteEvents": EventSerializer(incomplete_events, many=True).data,
                "isInCollege": is_in_college,
            },
            status=status.HTTP_200_OK,
        )

    elif request.method == "POST":
        action = request.data.get("eventAction")
        event_id = request.data.get("event_id")

        if action == "deleteEvent" and event_id:
            event_to_delete = get_object_or_404(
                Event, eventId=event_id, host=request.user
            )
            event_to_delete.delete()
            return Response(
                {"message": "Event deleted successfully"},
                status=status.HTTP_204_NO_CONTENT,
            )

        if "displayOnCollege" in request.data:
            event_to_update = get_object_or_404(
                Event, eventId=event_id, host=request.user
            )
            event_to_update.display_event_on_college = (
                request.data["displayOnCollege"] is True
            )
            event_to_update.save()
            return Response(
                {"message": "Event display setting updated"}, status=status.HTTP_200_OK
            )

        return Response(
            {"error": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST
        )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def createPaidEvent(request):
    user_account = get_object_or_404(CustomUser, username=request.user.username)
    event_action = request.data.get("eventAction")

    # Ensure valid event action
    if event_action != "submit":
        return Response(
            {"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST
        )

    # Pass user to the form explicitly
    event_form = EventForm(request.data, request.FILES, user=request.user)

    if event_form.is_valid():
        event = event_form.save(commit=False)
        event.host = user_account
        event.ticketing = "Paid"
        event.status = "live"

        host_profile, _ = HostProfile.objects.get_or_create(user=request.user)
        
        event.save()        

        # Create Stripe product
        product = createHostProduct(event, host_profile.stripe_account_id)
        if not product:
            event.delete()  # Prevent storing an incomplete event
            return Response(
                {"error": "Product creation failed."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        event.stripeProductId = product.id
        event.save()

        return Response(
            {"message": "Event is live!", "eventId": event.eventId},
            status=status.HTTP_201_CREATED,
        )

    return Response(
        {"errors": event_form.errors}, status=status.HTTP_400_BAD_REQUEST
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getHostStripeAccountLink(request):
    user_account = get_object_or_404(CustomUser, username=request.user.username)
    
    try:
        # Check if stripe account ID exists
        if not user_account.connectAccountID:
            return Response(
            {"error": "You aren't a host yet. Host your first event to get started."},
            status=status.HTTP_400_BAD_REQUEST,
        )
        
        # At this point we should have a valid stripe_account_id
        stripe_account_link = stripe.AccountLink.create(
            account=user_account.connectAccountID,
            refresh_url="https://waveoncampus.com/explore/",
            return_url="https://waveoncampus.com/explore/",
            type="account_onboarding",
        )

        return Response(
            {"url": stripe_account_link.url}, status=status.HTTP_200_OK
        )
    except Exception as e:
        # Log the specific error for debugging
        print(f"Stripe error: {str(e)}")
        return Response(
            {"error": f"Failed to get Stripe account link: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getEventFormFields(request):
    form = EventForm(user=request.user)  # Instantiate form with user context
    form_fields = {}

    for field_name, field in form.fields.items():
        field_data = {
            "type": field.__class__.__name__,  # Get field type
            "required": field.required,
            "label": field.label,
            "help_text": field.help_text,
        }

        # Include choices for ChoiceFields
        if isinstance(field, forms.ChoiceField):
            field_data["choices"] = field.choices

        form_fields[field_name] = field_data

    return Response({
        "formFields": form_fields,
        "placesKey": settings.PLACES_API_KEY
    }, status=status.HTTP_200_OK)


@api_view(["POST", "PATCH"])  # Add PATCH support
@permission_classes([IsAuthenticated])
def editEvent(request, eventId):
    """Update event details. Supports both full and partial updates."""
    event = get_object_or_404(Event, eventId=eventId)
    user_profile = UserProfile.objects.get(user=request.user)
    host_profile = HostProfile.objects.get(user=event.host)
    is_in_college = user_profile.college is not None

    # Use request.data instead of request.POST to support both form data and JSON
    data = request.data
    files = request.FILES

    # Handle partial updates for PATCH requests
    partial = request.method == "PATCH"
    
    edit_event_form = EditEventForm(data, files, instance=event, partial=partial)
    
    if edit_event_form.is_valid():
        updated_event = edit_event_form.save()
        
        # Get updated related data
        rsvp_list = RSVPTicket.objects.filter(event=updated_event).values()
        paid_free_tickets = PaidFreeTicket.objects.filter(event=updated_event).values()
        
        # Format location data
        location = {
            "building_name": updated_event.building_name,
            "street": updated_event.street,
            "apt_suite_unit": updated_event.apt_suite_unit,
            "city": updated_event.city,
            "state": updated_event.state,
            "zip_code": updated_event.zip_code,
            "country": updated_event.country,
            "hide_address": updated_event.hide_address
        }
        
        return Response({
            "message": "Event updated successfully.",
            "event": {
                "id": str(updated_event.eventId),
                "title": updated_event.title,
                "description": updated_event.description,
                "date": updated_event.date,
                "location": location,
                "host": {
                    "id": str(host_profile.hostProfileId),  # Use hostProfileId and convert UUID to string
                    "name": f"{host_profile.user.first_name} {host_profile.user.last_name}",  # Use direct name fields
                },
                "isInCollege": is_in_college,
                "rsvpList": list(rsvp_list),
                "paidFreeTickets": list(paid_free_tickets),
            }
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            "errors": edit_event_form.errors,
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def getHostEventTicketing(request, eventId):
    event = get_object_or_404(Event, eventId=eventId)
    try:
        ticketingType = event.ticketing
        
        if ticketingType == "Paid":
            ticket = PaidFreeTicket.objects.filter(event=event)
        else:
            ticket = RSVPTicket.objects.filter(event=event)
            
        return Response({
            "ticketingType": ticketingType,
            "tickets": TicketSerializer(ticket, many=True).data
        }, status=status.HTTP_200_OK)
    except:
        return Response({
            "error": "Failed to retrieve tickets."
        }, status=status.HTTP_400_BAD_REQUEST)
