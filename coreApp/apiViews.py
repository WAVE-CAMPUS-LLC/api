from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Count, Q
from django.utils.timezone import now
from datetime import timedelta, date
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from django.core.cache import cache
import json

import random
import logging

from eventManagementApp.models import Event, SharedEvent
from accountManagementApp.models import UserProfile
from eventTicketsApp.models import RSVPTicket, PaidFreeTicket
from eventTicketsApp.views import generateTicket
from socialApp.models import Crew
from .forms import RSVPForm
from .serializers import (
    ExplorePageEventSerializer,
    EventDetailSerializer,
    EventExtraPhotosSerializer,
)
from eventManagementApp.models import CouponCode, Event
from authenticationApp.models import CustomUser
from eventManagementApp.serializers import EventSerializer
from eventTicketsApp.serializers import RSVPTicketSerializer
from django.views.decorators.csrf import csrf_exempt


class GuestListCustomUserSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ("id", "username", "email", "first_name", "profile_picture")

    def get_profile_picture(self, obj):
        if (
            hasattr(obj, "user_profile")
            and obj.user_profile
            and obj.user_profile.profile_photo
        ):
            return obj.user_profile.profile_photo.url
        return None


@api_view(["GET"])
@permission_classes([AllowAny])
def explore_events(request):
    all_events = cache.get("live_events")
    if not all_events:
        all_events = Event.objects.filter(
            status="live", forAllDisplay=True, admin_status="active"
        ).only("eventId", "title", "date", "header_photo", "state", "city", "ticketing", "forAllDisplay", "forCollegesDisplay")
        cache.set("live_events", all_events, timeout=60 * 5)

    all_events_serialized = ExplorePageEventSerializer(all_events, many=True).data

    # Prepare response data
    response_data = {
        "events": all_events_serialized,
    }

    return Response(response_data)


@api_view(["GET"])
@permission_classes([AllowAny])
def event_details(request, eventId):
    # Fetch the event and related objects
    # cache_key = f"event_detail_{eventId}"
    # cached_data = cache.get(cache_key)
    # if cached_data:
    #     return Response({"event": cached_data})
    
    event = (
        Event.objects.filter(eventId=eventId)
        .only(
            "eventId",
            "title",
            "description",
            "date",
            "header_photo",
            "country",
            "street",
            "apt_suite_unit",
            "city",
            "state",
            "zip_code",
            "hide_address",
            "ticketing",
        )
        .first()
    )
    
    # Handle case where event doesn't exist
    if not event:
        return Response(
            {"error": "Event not found"}, 
            status=404
        )
    
    # Serialize and cache the result
    event_data = EventDetailSerializer(event).data
    # cache.set(cache_key, event_data, timeout=60 * 50)  # Cache for 50 minutes

    # Prepare response data
    response_data = {
        "event": event_data,
    }

    return Response(response_data)


def share_event_with_friend(request, eventId):
    event = get_object_or_404(Event, eventId=eventId)

    if not request.user.is_authenticated:
        return Response({"error": "Please login to share this event."}, status=401)

    friend_username = request.data.get("friendUsername")
    friend_user = get_object_or_404(UserProfile, user__username=friend_username)

    shared_event, created = SharedEvent.objects.get_or_create(
        sender=request.user.profile, receiver=friend_user, event=event
    )

    if created:
        return Response(
            {"message": f"Event shared with {friend_user.user.username}"}, status=201
        )
    else:
        return Response({"message": "Event already shared."}, status=200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_favorite(request, eventId):
    """
    API endpoint to toggle favorite status of an event.
    """
    user_profile = get_object_or_404(UserProfile, user=request.user)
    event = get_object_or_404(Event, eventId=eventId)
    action = request.data.get("eventAction")

    if action == "favoriteEvent":
        user_profile.favorite_events.add(event)
        return Response(
            {"status": "successfulFavorite", "message": "Event added to favorites."}
        )
    else:
        user_profile.favorite_events.remove(event)
        return Response(
            {
                "status": "successfulUnfavorite",
                "message": "Event removed from favorites.",
            }
        )


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def handle_rsvp(request, eventId):
    """
    API endpoint to handle RSVP for an event.
    """
    # Add debug logging
    logger = logging.getLogger(__name__)
    logger.info(f"RSVP request received for event {eventId}")
    logger.info(f"Request path: {request.path}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(
        f"Request user: {request.user} (authenticated: {request.user.is_authenticated})"
    )

    event = get_object_or_404(Event, eventId=eventId)

    existing_rsvp = (
        RSVPTicket.objects.filter(event=event, email=request.user.email).first()
        if request.user.is_authenticated
        else None
    )

    if existing_rsvp:
        logger.warning(f"User {request.user.email} already has an RSVP for this event")
        return Response(
            {"status": "error", "message": "This email has already been submitted!"},
            status=400,
        )

    rsvp_form = RSVPForm(request.data, user=request.user)
    if rsvp_form.is_valid():
        rsvp_ticket = rsvp_form.save(commit=False)

        if RSVPTicket.objects.filter(event=event, email=rsvp_ticket.email).exists():
            logger.warning(
                f"Email {rsvp_ticket.email} already has an RSVP for this event"
            )
            return Response(
                {
                    "status": "error",
                    "message": "This email has already been submitted! Try a different one.",
                },
                status=400,
            )

        if request.user.is_authenticated:
            user_profile = get_object_or_404(UserProfile, user=request.user)
            event.guest_list.add(user_profile.user)
            rsvp_ticket.first_name = request.user.first_name
            rsvp_ticket.last_name = request.user.last_name
            rsvp_ticket.email = request.user.email

        rsvp_ticket.event = event
        rsvp_ticket.save()

        generateTicket(
            request,
            event,
            request.user if request.user.is_authenticated else None,
            rsvp_ticket.first_name,
            rsvp_ticket.last_name,
            rsvp_ticket.email,
        )

        logger.info(f"RSVP successful for {rsvp_ticket.email}")
        return Response(
            {
                "status": "success",
                "message": "You have reserved a spot! Check your email for confirmation.",
            }
        )
    else:
        logger.error(f"RSVP form validation failed: {rsvp_form.errors}")
        return Response(
            {
                "status": "error",
                "message": "There was an error with your submission.",
                "errors": rsvp_form.errors,
            },
            status=400,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def event_guests(request, eventId):
    """
    API endpoint for getting the guest list of an event.
    Only shows guests if the event has show_guest_list set to True.
    Returns profile pictures, first names, and last names of guests.
    """
    # Fetch the event
    event = get_object_or_404(Event, eventId=eventId)

    # Check if the event allows showing the guest list
    if not event.show_guest_list:
        return Response(
            {"message": "Guest list is not available for this event."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Fetch the guest list
    guest_list = event.guest_list.all()

    # Prepare the response data with profile pictures and names
    guests_data = []
    for guest in guest_list:
        profile_picture = None
        if (
            hasattr(guest, "user_profile")
            and guest.user_profile
            and guest.user_profile.profile_photo
        ):
            profile_picture = guest.user_profile.profile_photo.url

        guests_data.append(
            {
                "id": str(guest.id),
                "first_name": guest.first_name,
                "last_name": guest.last_name,
                "profile_picture": profile_picture,
            }
        )

    return Response(
        {
            "event_id": str(event.eventId),
            "event_title": event.title,
            "guest_count": len(guests_data),
            "guests": guests_data,
        }
    )
