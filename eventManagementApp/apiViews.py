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
from .models import Event, HostProfile, EventPrivacy
from .serializers import EventSerializer, EventPrivacySerializer
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime
import uuid
from wave_v1.decorators import host, check_suspension
from stripeManagementApp.createHostProduct import createHostProduct

from accountManagementApp.models import UserProfile
from collegeManagementApp.models import Organization, OrganizationMembership
from .forms import HostApplicationForm, EventForm, EditEventForm
from eventTicketsApp.forms import InvitationForm, PaidFreeTicketForm
from .models import EventType, HostApplication, Event, EventPrivacy, HostProfile
from authenticationApp.models import CustomUser
from .utils import set_event_privacy


class CreateEventAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Extract data from the request
            event_data = {
                "title": request.data.get("title"),
                "description": request.data.get("description"),
                "event_type": request.data.get("event_type"),
                "date": request.data.get("date"),
                "start_time": datetime.strptime(
                    request.data.get("start_time"), "%H:%M"
                ).time(),  # Convert to time object
                # 'location': request.data.get('location'),
                # 'price': request.data.get('price'),
                # 'capacity': request.data.get('capacity'),
                "header_photo": request.FILES.get("header_photo"),
                "age_restriction": request.data.get("age_restriction"),
                "host": request.user,
                "status": "incomplete",
            }

            # Create the event
            event = Event.objects.create(**event_data)

            # Serialize and return the event
            serializer = EventSerializer(event)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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

        user_profile = event.host.user_profile
        host_profile, _ = HostProfile.objects.get_or_create(user=request.user)
        organization_membership = OrganizationMembership.objects.filter(
            user=event.host
        ).first()

        # Set privacy settings before saving
        privacy_set = set_event_privacy(
            event, user_profile, organization_membership, request
        )
        if not privacy_set:
            return Response(
                {"error": "Privacy setting failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
