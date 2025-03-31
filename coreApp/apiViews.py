from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Count, Q
from django.utils.timezone import now
from datetime import timedelta, date
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status

import random
import logging

from eventManagementApp.models import Event, SharedEvent
from accountManagementApp.models import UserProfile
from eventTicketsApp.models import RSVPTicket, PaidFreeTicket
from eventTicketsApp.views import generateTicket
from socialApp.models import Crew
from .forms import RSVPForm
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

@api_view(['GET'])
@permission_classes([AllowAny])
def explore_events(request):
    """
    API endpoint for getting explore page data including:
    - Initial events
    - Trending events
    - Weekly events
    - Trending categories
    - Invited events (for authenticated users)
    """
    # Load all events at once - no more pagination
    all_events = Event.objects.filter(
        status="live", 
        forAllDisplay=True,
        admin_status="active"
    )

    # Get trending events
    trending_events = Event.objects.filter(
        status="live", 
        forAllDisplay=True,
        admin_status="active"
    ).order_by("date")[:3]

    # Get invited events for authenticated users
    invited_events_data = []
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            invited_events = user_profile.invited_events.filter(status="live")
            invitations = user_profile.invitations.all()
            
            for event in invited_events:
                token = next((invite.token for invite in invitations if invite.event == event), None)
                event_serializer = EventSerializer(event)
                invited_events_data.append({
                    'event': event_serializer.data,
                    'token': str(token) if token else None
                })
        except UserProfile.DoesNotExist:
            pass

    # Replace the trending categories section with all categories
    all_categories = []
    for category_type, category_name in Event.EXPLORE_TYPE_CHOICES:
        count = Event.objects.filter(
            status="live",
            admin_status="active",
            event_type=category_type
        ).count()
        
        all_categories.append({
            'type': category_type,
            'display_name': category_name,
            'count': count
        })

    # Sort categories by count in descending order
    all_categories.sort(key=lambda x: x['count'], reverse=True)

    # Get weekly events
    today = now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    weekly_events = Event.objects.filter(
        date__range=[start_of_week, end_of_week],
        status="live",
        admin_status="active",
    ).order_by("?")[:3]

    # Prepare response data using serializers
    all_events_serialized = EventSerializer(all_events, many=True).data
    trending_events_serialized = EventSerializer(trending_events, many=True).data
    weekly_events_serialized = EventSerializer(weekly_events, many=True).data
    
    # Add college name for events with display_event_on_college=True
    for events_list in [all_events_serialized, trending_events_serialized, weekly_events_serialized]:
        for event_data in events_list:
            event_obj = next((e for e in all_events if str(e.eventId) == event_data['eventId']), None)
            if event_obj and event_obj.display_event_on_college and event_obj.host and hasattr(event_obj.host, 'user_profile') and event_obj.host.user_profile.college:
                event_data['college_name'] = event_obj.host.user_profile.college.name
    
    # Prepare response data
    response_data = {
        'events': all_events_serialized,  # All events in a single list
        'trending_events': trending_events_serialized,
        'weekly_events': weekly_events_serialized,
        'trending_categories': all_categories,
        'invited_events': invited_events_data
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

        # Calculate user's age if not already stored
        user_age = request.user.age
        if user_age is None and request.user.birthday:
            today = date.today()
            user_age = (today.year - request.user.birthday.year) - (
                (today.month, today.day)
                < (request.user.birthday.month, request.user.birthday.day)
            )
            request.user.age = user_age
            request.user.save()
    else:
        user_age = None  # Anonymous users don't have age available

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
                couponCode = request.data.get("couponCode")
                coupon = get_object_or_404(CouponCode, code=couponCode)
            except coupon.DoesNotExist:
                return Response({"message": "Invalid coupon code."}, status=status.HTTP_400_BAD_REQUEST)
            
            if coupon.is_valid():
                # Return success response with discount information
                discount_data = {
                    "status": "success", 
                    "message": "Valid coupon code applied successfully"
                }
                
                # Only add these fields if they exist
                if hasattr(coupon, 'discount_percentage'):
                    discount_data["discount_percentage"] = coupon.discount_percentage
                    
                return Response(discount_data, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Coupon is not valid anymore."}, status=status.HTTP_400_BAD_REQUEST)
            

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