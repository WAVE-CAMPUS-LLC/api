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
from .serializers import ExplorePageEventSerializer
from eventManagementApp.models import CouponCode, Event
from authenticationApp.models import CustomUser
from eventManagementApp.serializers import EventSerializer
from eventTicketsApp.serializers import RSVPTicketSerializer
from django.views.decorators.csrf import csrf_exempt

class GuestListCustomUserSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'first_name', 'profile_picture')
        
    def get_profile_picture(self, obj):
        if hasattr(obj, 'user_profile') and obj.user_profile and obj.user_profile.profile_photo:
            return obj.user_profile.profile_photo.url
        return None

def explore_events(request):
    all_events = cache.get("live_events")
    if not all_events:
        all_events = Event.objects.filter(
            status="live", forAllDisplay=True, admin_status="active"
        ).only("eventId", "title", "date", "header_photo", "state", "city", "ticketing", "forAllDisplay", "forCollegesDisplay")
        cache.set("live_events", all_events, timeout=60 * 5)

    all_events_serialized = ExplorePageEventSerializer(all_events, many=True).data

    # Add college name for events with display_event_on_college=True
    for events_list in [all_events_serialized]:
        for event_data in events_list:
            event_obj = next(
                (e for e in all_events if str(e.eventId) == event_data["eventId"]), None
            )
            if (
                event_obj
                and event_obj.display_event_on_college
                and event_obj.host
                and hasattr(event_obj.host, "user_profile")
                and event_obj.host.user_profile.college
            ):
                event_data["college_name"] = event_obj.host.user_profile.college.name

    # Prepare response data
    response_data = {
        "events": all_events_serialized,
    }

    return Response(response_data)

@api_view(['GET'])
@permission_classes([AllowAny])
def load_more_events(request):
    """
    API endpoint for loading more events with pagination
    """
    offset = int(request.GET.get("offset", 7))
    limit = 3

    more_events = Event.objects.filter(
        status="live", privacy="Discoverable", admin_status="active"
    )[offset : offset + limit]

    events_data = [{
        'id': str(event.eventId),
        'title': event.title,
        'date': event.date,
        'header_photo': event.header_photo.url if event.header_photo else None,
        'host': event.host.username if event.host else None,
        'status': event.status
    } for event in more_events]

    has_more = Event.objects.filter(
        status="live", privacy="Discoverable", admin_status="active"
    ).count() > (offset + limit)

    return Response({
        'events': events_data,
        'has_more': has_more
    })


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def event_details(request, eventId):
    """
    API endpoint for getting event details, including:
    - Event info
    - RSVP management
    - Event sharing
    - Favorite/unfavorite actions
    - Ticket purchasing for crews
    """
    
    # Fetch the event and related objects
    event = get_object_or_404(Event, eventId=eventId)
    eventPaidFreeTickets = PaidFreeTicket.objects.filter(event=event)
    
    # Check for RSVP requirement and guest list
    rsvpFormRequired = event.ticketing == "RSVP Required"  # Just a boolean flag indicating if RSVP is required
    
    guest_list = event.guest_list.all()
    user = None
    user_friends = None
    user_crews = None

    if request.user.is_authenticated:
        user = get_object_or_404(UserProfile, user=request.user)
        user_friends = user.friends.all()
        user_crews = user.get_all_crews()

        
    # Check if the event is a favorite event for the current user
    isFavoriteEvent = False
    if user and hasattr(user, "favorite_events"):
        isFavoriteEvent = user.favorite_events.filter(eventId=event.eventId).exists()

    # Handle POST actions (RSVP, share, favorite/unfavorite, purchase)
    if request.method == "POST":
        action = request.data.get("eventAction")

        if action == "RSVP":
            user_email = request.data.get("email")
            existing_rsvp = RSVPTicket.objects.filter(event=event, email=user_email).first()

            if existing_rsvp:
                return Response(
                    {"message": "This email has already been submitted! Try a different one."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                rsvp_ticket = RSVPTicketSerializer(data=request.data)
                if rsvp_ticket.is_valid():
                    rsvp_ticket.save()
                    return Response(
                        {"message": "You have reserved a spot! Check your email for confirmation."},
                        status=status.HTTP_201_CREATED
                    )

        elif action == "shareEventWithFriend":
            if not request.user.is_authenticated:
                return Response({"message": "Please login to share this event."}, status=status.HTTP_400_BAD_REQUEST)
            
            friend_username = request.data.get("shareFriendUsername")
            friendUserAccount = get_object_or_404(CustomUser, username=friend_username)
            friend = get_object_or_404(UserProfile, user=friendUserAccount)

            shared_event, created = SharedEvent.objects.get_or_create(sender=user, receiver=friend, event=event)

            if created:
                return Response({"message": f"Event shared with {friend}"}, status=status.HTTP_200_OK)
            else:
                return Response({"message": f"Event already shared with {friend}"}, status=status.HTTP_400_BAD_REQUEST)

        elif action == "shareEventWithCrew":
            if not request.user.is_authenticated:
                return Response({"message": "Please login to share this event."}, status=status.HTTP_400_BAD_REQUEST)

            crew_id = request.data.get("shareCrewId")
            crew = get_object_or_404(Crew, crewId=crew_id)

            for member in crew.members.all():
                SharedEvent.objects.get_or_create(crew=crew, sender=user, receiver=member.user_profile, event=event)

            return Response({"message": f"Event shared with {crew.name}"}, status=status.HTTP_200_OK)

        elif action == "favoriteEvent":
            if not request.user.is_authenticated:
                return Response({"message": "Please login to favorite this event."}, status=status.HTTP_400_BAD_REQUEST)

            user.favorite_events.add(event)
            return Response({"message": "Event added to your favorites."}, status=status.HTTP_200_OK)

        elif action == "unfavoriteEvent":
            if not request.user.is_authenticated:
                return Response({"message": "Please login to unfavorite this event."}, status=status.HTTP_400_BAD_REQUEST)

            user.favorite_events.remove(event)
            return Response({"message": "Event removed from your favorites."}, status=status.HTTP_200_OK)

        elif action == "purchaseForCrew":
            if not request.user.is_authenticated:
                return Response({"message": "Please login to purchase tickets for a crew."}, status=status.HTTP_400_BAD_REQUEST)
            
            crew_id = request.data.get("crewId")
            ticketId = request.data.get("ticketId")

            return Response(
                {"message": "Redirecting to crew checkout."}, 
                status=status.HTTP_200_OK
            )
            
        elif action == "applyCouponCode":
            try:
                # Get required parameters
                coupon_code = request.data.get("couponCode")
                
                if not coupon_code:
                    return Response({
                        "success": False,
                        "message": "Coupon code is required"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Validate the coupon code
                try:
                    coupon = CouponCode.objects.get(code=coupon_code, event=event)
                except CouponCode.DoesNotExist:
                    return Response({
                        "success": False,
                        "message": "Invalid coupon code for this event"
                    }, status=status.HTTP_404_NOT_FOUND)
                
                # Check if coupon is valid
                if coupon.is_valid():
                    # Get the current cart
                    cart = request.session.get("cart", {})
                    
                    # Add the coupon code to the cart
                    cart['coupon_code'] = coupon_code
                    
                    # Save the updated cart back to the session
                    request.session["cart"] = cart
                    
                    # Return success response with discount information
                    return Response({
                        "success": True,
                        "message": "Coupon applied successfully",
                        "discount_percentage": coupon.discount_percentage
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        "success": False,
                        "message": "Coupon is not valid anymore."
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except json.JSONDecodeError:
                return Response({
                    "success": False,
                    "message": "Invalid JSON format"
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({
                    "success": False,
                    "message": f"An error occurred: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            

    # Prepare response data
    response_data = {
        "event": EventSerializer(event).data,
        
        "rsvpFormRequired": rsvpFormRequired,  # Boolean indicating if RSVP form is required
        "paidFreeTickets": eventPaidFreeTickets.values(),
        "friends": [GuestListCustomUserSerializer(user_friend.user).data for user_friend in user_friends] if user_friends else [],
        "crews": [user_crew.name for user_crew in user_crews] if user_crews else [],
        "isFavoriteEvent": isFavoriteEvent,
        "guestList": [GuestListCustomUserSerializer(guest).data for guest in guest_list] if guest_list else [],
    }

    return Response(response_data)



def share_event_with_friend(request, eventId):
    event = get_object_or_404(Event, eventId=eventId)

    if not request.user.is_authenticated:
        return Response({"error": "Please login to share this event."}, status=401)

    friend_username = request.data.get('friendUsername')
    friend_user = get_object_or_404(UserProfile, user__username=friend_username)

    shared_event, created = SharedEvent.objects.get_or_create(sender=request.user.profile, receiver=friend_user, event=event)

    if created:
        return Response({"message": f"Event shared with {friend_user.user.username}"}, status=201)
    else:
        return Response({"message": "Event already shared."}, status=200)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_favorite(request, eventId):
    """
    API endpoint to toggle favorite status of an event.
    """
    user_profile = get_object_or_404(UserProfile, user=request.user)
    event = get_object_or_404(Event, eventId=eventId)
    action = request.data.get('eventAction')
    
    if action == "favoriteEvent":
        user_profile.favorite_events.add(event)
        return Response({"status": "successfulFavorite", "message": "Event added to favorites."})
    else:
        user_profile.favorite_events.remove(event)
        return Response({"status": "successfulUnfavorite", "message": "Event removed from favorites."})


@csrf_exempt
@api_view(['POST'])
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
    logger.info(f"Request user: {request.user} (authenticated: {request.user.is_authenticated})")
    
    event = get_object_or_404(Event, eventId=eventId)
    
    existing_rsvp = RSVPTicket.objects.filter(event=event, email=request.user.email).first() if request.user.is_authenticated else None
    
    if existing_rsvp:
        logger.warning(f"User {request.user.email} already has an RSVP for this event")
        return Response({"status": "error", "message": "This email has already been submitted!"}, status=400)
    
    rsvp_form = RSVPForm(request.data, user=request.user)
    if rsvp_form.is_valid():
        rsvp_ticket = rsvp_form.save(commit=False)
        
        if RSVPTicket.objects.filter(event=event, email=rsvp_ticket.email).exists():
            logger.warning(f"Email {rsvp_ticket.email} already has an RSVP for this event")
            return Response({"status": "error", "message": "This email has already been submitted! Try a different one."}, status=400)
        
        if request.user.is_authenticated:
            user_profile = get_object_or_404(UserProfile, user=request.user)
            event.guest_list.add(user_profile.user)
            rsvp_ticket.first_name = request.user.first_name
            rsvp_ticket.last_name = request.user.last_name
            rsvp_ticket.email = request.user.email
        
        rsvp_ticket.event = event
        rsvp_ticket.save()
        
        generateTicket(request, event, request.user if request.user.is_authenticated else None, rsvp_ticket.first_name, rsvp_ticket.last_name, rsvp_ticket.email)
        
        logger.info(f"RSVP successful for {rsvp_ticket.email}")
        return Response({"status": "success", "message": "You have reserved a spot! Check your email for confirmation."})
    else:
        logger.error(f"RSVP form validation failed: {rsvp_form.errors}")
        return Response({"status": "error", "message": "There was an error with your submission.", "errors": rsvp_form.errors}, status=400)


@api_view(['GET'])
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
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Fetch the guest list
    guest_list = event.guest_list.all()
    
    # Prepare the response data with profile pictures and names
    guests_data = []
    for guest in guest_list:
        profile_picture = None
        if hasattr(guest, 'user_profile') and guest.user_profile and guest.user_profile.profile_photo:
            profile_picture = guest.user_profile.profile_photo.url
            
        guests_data.append({
            'id': str(guest.id),
            'first_name': guest.first_name,
            'last_name': guest.last_name,
            'profile_picture': profile_picture,
        })
    
    return Response({
        "event_id": str(event.eventId),
        "event_title": event.title,
        "guest_count": len(guests_data),
        "guests": guests_data
    })