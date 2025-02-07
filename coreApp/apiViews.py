from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Count, Q
from django.utils.timezone import now
from datetime import timedelta, date
from django.shortcuts import get_object_or_404

import random

from eventManagementApp.models import Event, SharedEvent
from accountManagementApp.models import UserProfile
from eventTicketsApp.models import RSVPTicket, PaidFreeTicket
from .forms import RSVPForm
from .serializers import EventSerializer
from eventTicketsApp.serializers import RSVPTicketSerializer
from eventTicketsApp.models import RSVPTicket, PaidFreeTicket
from eventManagementApp.models import EventPrivacy

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
    # Handle age restrictions
    if not request.user.is_authenticated:
        age_filter = Q(age_restriction="")
    else:
        user_age = request.user.age
        if user_age is None and request.user.birthday:
            today = date.today()
            user_age = (today.year - request.user.birthday.year) - (
                (today.month, today.day)
                < (request.user.birthday.month, request.user.birthday.day)
            )
            request.user.age = user_age
            request.user.save()

        age_filter = Q(age_restriction="")
        if user_age:
            if user_age >= 21:
                age_filter |= Q(age_restriction="21+")
            if user_age >= 18:
                age_filter |= Q(age_restriction="18+")

    # Load initial events
    initial_events = Event.objects.filter(
        status="live", privacy="Discoverable", admin_status="active"
    )[:7]

    # Get trending events
    trending_events = Event.objects.filter(
        status="live", privacy="Discoverable"
    ).order_by("date")[:3]

    # Get invited events for authenticated users
    invited_events_data = []
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            invited_events = user_profile.invited_events.filter(status="live").filter(age_filter)
            invitations = user_profile.invitations.all()
            
            for event in invited_events:
                token = next((invite.token for invite in invitations if invite.event == event), None)
                invited_events_data.append({
                    'event': {
                        'id': str(event.eventId),
                        'title': event.title,
                        'date': event.date,
                        'header_photo': event.header_photo.url if event.header_photo else None,
                        'host': event.host.username if event.host else None,
                    },
                    'token': str(token) if token else None
                })
        except UserProfile.DoesNotExist:
            pass

    # Get trending categories
    trending_categories = (
        Event.objects.filter(
            status="live", privacy="Discoverable", admin_status="active"
        )
        .values("event_type")
        .annotate(event_count=Count("event_type"))
        .order_by("-event_count")[:4]
    )

    trending_category_choices = []
    for category in trending_categories:
        event_type = category["event_type"]
        display_name = dict(Event.EXPLORE_TYPE_CHOICES).get(event_type, event_type)
        trending_category_choices.append({
            'type': event_type,
            'display_name': display_name,
            'count': category['event_count']
        })

    # Fill remaining categories if needed
    if len(trending_category_choices) < 4:
        remaining_choices = list(
            set(Event.EXPLORE_TYPE_CHOICES) - set((c['type'], c['display_name']) for c in trending_category_choices)
        )
        additional_choices = random.sample(
            remaining_choices, 4 - len(trending_category_choices)
        )
        for choice_type, choice_name in additional_choices:
            trending_category_choices.append({
                'type': choice_type,
                'display_name': choice_name,
                'count': 0
            })

    # Get weekly events
    today = now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    weekly_events = Event.objects.filter(
        date__range=[start_of_week, end_of_week],
        status="live",
        privacy="Discoverable",
        admin_status="active",
    ).order_by("?")[:3]

    # Prepare response data
    response_data = {
        'initial_events': [{
            'id': str(event.eventId),
            'title': event.title,
            'date': event.date,
            'header_photo': event.header_photo.url if event.header_photo else None,
            'host': event.host.username if event.host else None,
            'status': event.status
        } for event in initial_events],
        'trending_events': [{
            'id': str(event.eventId),
            'title': event.title,
            'date': event.date,
            'header_photo': event.header_photo.url if event.header_photo else None,
            'host': event.host.username if event.host else None,
        } for event in trending_events],
        'weekly_events': [{
            'id': str(event.eventId),
            'title': event.title,
            'date': event.date,
            'header_photo': event.header_photo.url if event.header_photo else None,
            'host': event.host.username if event.host else None,
        } for event in weekly_events],
        'trending_categories': trending_category_choices,
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

    if not request.user.is_authenticated:
        age_filter = Q(age_restriction="")
    else:
        user_age = request.user.age
        if user_age is None and request.user.birthday:
            today = date.today()
            user_age = (today.year - request.user.birthday.year) - (
                (today.month, today.day)
                < (request.user.birthday.month, request.user.birthday.day)
            )
            request.user.age = user_age
            request.user.save()

        age_filter = Q(age_restriction="")
        if user_age:
            if user_age >= 21:
                age_filter |= Q(age_restriction="21+")
            if user_age >= 18:
                age_filter |= Q(age_restriction="18+")

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
    
    event = get_object_or_404(Event, eventId=eventId)
    eventprivacy = EventPrivacy.objects.get(event=event)
    eventPaidFreeTickets = PaidFreeTicket.objects.filter(event=event)
    
    # Check for RSVP requirement and guest list
    rsvpForm = None
    if event.ticketing == "RSVP Required":
        rsvpForm = RSVPForm()

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

    # Return event details as JSON
    response_data = {
        "event": EventSerializer(event).data,
        "eventPrivacy": {
            "require_invitation": eventprivacy.require_invitation,
            "restricted_college": eventprivacy.restricted_college,
            "restricted_organization": eventprivacy.restricted_organization,
        },
        "rsvpForm": rsvpForm,  # Add if needed
        "paidFreeTickets": eventPaidFreeTickets.values(),
        "friends": [user_friend.username for user_friend in user_friends] if user_friends else [],
        "crews": [user_crew.name for user_crew in user_crews] if user_crews else [],
        "isFavoriteEvent": isFavoriteEvent,
        "guestList": [guest.username for guest in guest_list] if guest_list else [],
    }

    return Response(response_data)



def handle_rsvp(request, eventId):
    event = get_object_or_404(Event, eventId=eventId)

    # Extract user information and validate RSVP
    email = request.data.get('email')
    existing_rsvp = RSVPTicket.objects.filter(event=event, email=email).first()

    if existing_rsvp:
        return Response({"error": "This email has already been submitted! Try a different one."}, status=400)

    rsvp_ticket = RSVPTicket.objects.create(event=event, email=email)
    return Response({"message": "You have reserved a spot! Check your email for confirmation."}, status=201)


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


def favorite_event(request, eventId):
    event = get_object_or_404(Event, eventId=eventId)
    user_profile = get_object_or_404(UserProfile, user=request.user)

    user_profile.favorite_events.add(event)
    return Response({"message": "Event added to your favorites."}, status=200)

def unfavorite_event(request, eventId):
    event = get_object_or_404(Event, eventId=eventId)
    user_profile = get_object_or_404(UserProfile, user=request.user)

    user_profile.favorite_events.remove(event)
    return Response({"message": "Event removed from your favorites."}, status=200)
