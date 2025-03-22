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
from eventTicketsApp.serializers import (
    TicketSerializer,
    PaidFreeTicketSerializer,
    RSVPTicketSerializer,
    CouponSerializer,
)
from .serializers import EventSerializer
from eventManagementApp.models import CouponCode, Event
from eventTicketsApp.forms import InvitationForm, PaidFreeTicketForm
from .models import EventType, HostApplication, Event, HostProfile
from authenticationApp.models import CustomUser
from eventTicketsApp.models import RSVPTicket, PaidFreeTicket
from stripeManagementApp.createHostProduct import createHostProduct
from stripeManagementApp.createHostProductPrice import createProductPriceType


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

    return Response({"errors": event_form.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getHostStripeAccountLink(request):
    user_account = get_object_or_404(CustomUser, username=request.user.username)

    try:
        # Check if stripe account ID exists
        if not user_account.connectAccountID:
            return Response(
                {
                    "error": "You aren't a host yet. Host your first event to get started."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # At this point we should have a valid stripe_account_id
        stripe_login_link = stripe.Account.create_login_link(
            user_account.connectAccountID
        )

        return Response({"url": stripe_login_link.url}, status=status.HTTP_200_OK)
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

    return Response(
        {"formFields": form_fields, "placesKey": settings.PLACES_API_KEY},
        status=status.HTTP_200_OK,
    )


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
            "hide_address": updated_event.hide_address,
        }

        return Response(
            {
                "message": "Event updated successfully.",
                "event": {
                    "id": str(updated_event.eventId),
                    "title": updated_event.title,
                    "description": updated_event.description,
                    "date": updated_event.date,
                    "location": location,
                    "host": {
                        "id": str(
                            host_profile.hostProfileId
                        ),  # Use hostProfileId and convert UUID to string
                        "name": f"{host_profile.user.first_name} {host_profile.user.last_name}",  # Use direct name fields
                    },
                    "isInCollege": is_in_college,
                    "rsvpList": list(rsvp_list),
                    "paidFreeTickets": list(paid_free_tickets),
                },
            },
            status=status.HTTP_200_OK,
        )
    else:
        return Response(
            {
                "errors": edit_event_form.errors,
                "message": "Failed to update event.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )



# Ticketing and RSVP Management
@api_view(["POST", "GET", "DELETE", "PATCH", "PUT", "OPTIONS"])
@permission_classes([IsAuthenticated])
def getRSVPTicketsForEvent(request, eventId):
    # First, get the event and check if the requesting user is the host
    event = get_object_or_404(Event, eventId=eventId)

    # Check if the requesting user is the host of the event
    if event.host != request.user:
        return Response(
            {
                "error": "You don't have permission to access these tickets. Only the event host can view ticket information."
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # Handle DELETE request for RSVP tickets
    if request.method == "DELETE":
        ticket_id = request.data.get("ticket_id")
        if not ticket_id:
            return Response(
                {"error": "Missing ticket ID."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # First try to find and delete the RSVP ticket
            rsvp_ticket = RSVPTicket.objects.get(id=ticket_id, event=event)
            
            # Also find and delete any associated actual ticket with QR code
            try:
                # More specific matching criteria to find the correct associated tickets
                # Using a combination of identifiers that would uniquely match the RSVP to tickets
                tickets_to_delete = Ticket.objects.filter(
                    event=event,
                    email=rsvp_ticket.email
                )
                
                # If user is available, further refine the query
                if rsvp_ticket.user:
                    tickets_to_delete = tickets_to_delete.filter(user=rsvp_ticket.user)
                
                # Optionally add more matching criteria if available in your models
                # For example, if both models have a name field:
                if hasattr(rsvp_ticket, 'name') and rsvp_ticket.name:
                    tickets_to_delete = tickets_to_delete.filter(name=rsvp_ticket.name)
                
                deleted_count = tickets_to_delete.count()
                tickets_to_delete.delete()
                
                # Log the deletion for debugging purposes
                print(f"Deleted {deleted_count} tickets associated with RSVP {ticket_id}")
            except Exception as e:
                # Continue even if no associated tickets found
                print(f"Error while deleting associated tickets: {str(e)}")
                deleted_count = 0
            
            # Delete the RSVP ticket itself
            rsvp_ticket.delete()
            
            return Response(
                {
                    "message": f"RSVP deleted successfully with {deleted_count} associated ticket(s)."
                },
                status=status.HTTP_200_OK
            )
        except RSVPTicket.DoesNotExist:
            return Response(
                {"error": "RSVP ticket not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to delete RSVP: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # Get RSVP tickets for the event
    rsvp_list = RSVPTicket.objects.filter(event=event)

    # Get actual purchased tickets for the event
    purchased_tickets = Ticket.objects.filter(event=event)
    
    return Response(
        {
            "rsvpList": RSVPTicketSerializer(rsvp_list, many=True).data,
            "purchasedTickets": TicketSerializer(purchased_tickets, many=True).data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def getPaidFreeTicketsForEvent(request, eventId):
    """
    GET: Retrieve all paid/free tickets for an event
    POST: Create a new ticket for an event
    DELETE: Delete a specific ticket

    Requires authentication. User must be the event host.
    """
    event = get_object_or_404(Event, eventId=eventId)

    # Check if the requesting user is the host of the event
    if event.host != request.user:
        return Response(
            {"error": "You don't have permission to manage tickets for this event."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Get ticket types available for the event
    paid_free_tickets = PaidFreeTicket.objects.filter(event=event)

    # Get actual purchased tickets for the event
    purchased_tickets = Ticket.objects.filter(event=event)

    if request.method == "DELETE":
        ticket_id = request.data.get("ticket_id")
        if not ticket_id:
            return Response(
                {"error": "Missing ticket ID."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            ticket = PaidFreeTicket.objects.get(ticket_id=ticket_id, event=event)
            ticket.delete()
            return Response(
                {"message": "Ticket deleted successfully."},
                status=status.HTTP_204_NO_CONTENT,
            )
        except PaidFreeTicket.DoesNotExist:
            return Response(
                {"error": "Ticket not found."}, status=status.HTTP_404_NOT_FOUND
            )

    elif request.method == "POST":
        action = request.data.get("eventAction")

        if action != "createTicket":
            return Response(
                {"error": "Invalid action. Use 'createTicket' to create a new ticket."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            hostProfile = HostProfile.objects.get(user=event.host)
        except HostProfile.DoesNotExist:
            return Response(
                {"error": "Host profile not found."}, status=status.HTTP_404_NOT_FOUND
            )

        paidFreeForm = PaidFreeTicketForm(request.data)
        if paidFreeForm.is_valid():
            ticket = paidFreeForm.save(commit=False)
            ticket.event = event
            ticket.save()

            try:
                eventStripeId = event.stripeProductId
                if not eventStripeId:
                    return Response(
                        {"error": "Event does not have a valid Stripe product ID."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                stripePrice = createProductPriceType(
                    eventStripeId,
                    ticket.ticket_price,
                    hostProfile.stripe_account_id,
                    ticket.ticket_quantity,
                )

                ticket.stripePriceId = stripePrice.id
                ticket.save()

                return Response(
                    {
                        "message": "Ticket created successfully.",
                        "ticket": PaidFreeTicketSerializer(ticket).data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            except Exception as e:
                # Rollback the ticket creation if Stripe integration fails
                ticket.delete()
                return Response(
                    {"error": f"Failed to create Stripe price: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            return Response(
                {"errors": paidFreeForm.errors}, status=status.HTTP_400_BAD_REQUEST
            )

    # Default GET response
    return Response(
        {
            "paidFreeTickets": PaidFreeTicketSerializer(
                paid_free_tickets, many=True
            ).data,
            "purchasedTickets": TicketSerializer(purchased_tickets, many=True).data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getPaidTicketFormFields(request):
    form = PaidFreeTicketForm()
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
    return Response(
        {
            "formFields": form_fields,
            "placesKey": settings.PLACES_API_KEY,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST", "GET", "DELETE", "PATCH", "PUT", "OPTIONS"])
@permission_classes([IsAuthenticated])
def getCouponsForEvent(request, eventId):
    event = get_object_or_404(Event, eventId=eventId)
    coupons = CouponCode.objects.filter(event=event)
    
    if request.method == "POST":
        coupon_code = request.data.get("coupon_code")
        discount = request.data.get("discount")
        expiry_date = request.data.get("expiry_date")

        if not coupon_code or not discount or not expiry_date:
            return Response(
                {"error": "Missing required fields."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            expiry_date = datetime.strptime(expiry_date, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        coupon = CouponCode.objects.create(
            event=event,
            code=coupon_code,
            discount=discount,
            expiry_date=expiry_date,
        )
        coupon.save()

        return Response(
            {
                "message": "Coupon created successfully.",
                "coupon": CouponSerializer(coupon).data,
            },
            status=status.HTTP_201_CREATED,
        )

    elif request.method == "DELETE":
        coupon_id = request.data.get("coupon_id")
        if not coupon_id:
            return Response(
                {"error": "Missing coupon ID."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Try different ways to find the coupon - by id or by coupon_id
            try:
                coupon = CouponCode.objects.get(id=coupon_id, event=event)
            except (CouponCode.DoesNotExist, ValueError):
                # If id doesn't work, try with coupon_id as a string field
                coupon = CouponCode.objects.get(code=coupon_id, event=event)
            
            coupon.delete()
            return Response(
                {"message": "Coupon deleted successfully."},
                status=status.HTTP_204_NO_CONTENT,
            )
        except CouponCode.DoesNotExist:
            return Response(
                {"error": "Coupon not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to delete coupon: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return Response(
        {
            "coupons": CouponSerializer(coupons, many=True).data
        },
        status=status.HTTP_200_OK,
    )
