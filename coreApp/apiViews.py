from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Count, Q
from django.utils.timezone import now
from datetime import timedelta, date
import random

from eventManagementApp.models import Event
from accountManagementApp.models import UserProfile
from eventTicketsApp.models import RSVPTicket, PaidFreeTicket

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
