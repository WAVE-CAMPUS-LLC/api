from django.shortcuts import get_object_or_404, render, redirect
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.http import JsonResponse
import random
from django.db.models import Count, Q, Exists, OuterRef
from django.http import JsonResponse
from datetime import datetime, timedelta, date
from django.contrib import messages
from django.utils.timezone import now

from socialApp.views import send_social_socket_message
from .models import Visitor
from authenticationApp.models import CustomUser
from eventManagementApp.models import (
    Event,
    InviteEventOption,
    SharedEvent,
)
from socialApp.models import FriendRequest, Crew
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from eventTicketsApp.models import RSVPTicket, PaidFreeTicket
from accountManagementApp.models import UserProfile
from .forms import RSVPForm
from collegeManagementApp.models import OrganizationMembership
from eventTicketsApp.views import generateTicket
from eventTicketsApp.models import Ticket
from django.conf import settings
from django.urls import reverse

# Create your views here.
def indexView(request):
    pageName = "home"
    return render(request, "coreApp/index.html", {"page": pageName})


def exploreView(request):
    pageName = "explore"

    user = None
    user_friends = None
    user_crews = None

    if request.user.is_authenticated:
        user = get_object_or_404(UserProfile, user=request.user)
        user_friends = user.friends.all()
        user_crews = user.get_all_crews()

    else:
        # Anonymous users cannot bypass age restrictions
        user_age = None

    isFavoriteEvent = []

    if user and hasattr(user, "favorite_events"):
        favorite_events = user.favorite_events.all()
        isFavoriteEvent = [event.eventId for event in favorite_events]

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

    # Load initial 6 events
    initial_events = Event.objects.filter(
        status="live", 
        forAllDisplay=True,  # Changed from privacy="Discoverable"
        admin_status="active"
    )[:9]
    
    trending_events = Event.objects.filter(
        status="live",
        forAllDisplay=True  # Changed from privacy="Discoverable"
    ).order_by("date")[:3]

    # Retrieve the user profile and invited events
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        invited_events = user_profile.invited_events.filter(status="live").filter(
            age_filter
        )
        invitations = user_profile.invitations.all()
        invited_events_with_tokens = []
        for event in invited_events:
            token = None
            for invite in invitations:
                if invite.event == event:
                    token = invite.token
                    break
            invited_events_with_tokens.append((event, token))
    except (TypeError, AttributeError, UserProfile.DoesNotExist):
        user_profile = None
        invited_events_with_tokens = None

    trending_categories = (
        Event.objects.filter(
            status="live", forAllDisplay=True, admin_status="active"
        )
        .values("event_type")
        .annotate(event_count=Count("event_type"))
        .order_by("-event_count")[:4]
    )

    trending_category_choices = []
    for category in trending_categories:
        event_type = category["event_type"]
        display_name = dict(Event.EXPLORE_TYPE_CHOICES).get(event_type, event_type)
        trending_category_choices.append((event_type, display_name))
    print(trending_category_choices)

    if len(trending_category_choices) < 4:
        remaining_choices = list(
            set(Event.EXPLORE_TYPE_CHOICES) - set(trending_category_choices)
        )
        additional_choices = random.sample(
            remaining_choices, 4 - len(trending_category_choices)
        )
        trending_category_choices += additional_choices

    today = now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    weekly_events = Event.objects.filter(
        date__range=[start_of_week, end_of_week],
        status="live",
        forAllDisplay=True,
        admin_status="active",
    ).order_by("?")[:3]

    return render(
        request,
        "coreApp/explore.html",
        {
            "page": pageName,
            "events": initial_events,
            "trending_events": trending_events,
            "weekly_events": weekly_events,
            "exploreCategoryChoices": trending_category_choices,
            "invited_events_with_tokens": invited_events_with_tokens,
            "isFavoriteEvent": isFavoriteEvent,
        },
    )


def categoriesView(request):
    pageName = "explore"

    explore_category_choices = Event.EXPLORE_TYPE_CHOICES

    return render(
        request,
        "coreApp/categories.html",
        {
            "page": pageName,
            "exploreCategoryChoices": explore_category_choices,
        },
    )


def load_more_events(request):
    offset = int(request.GET.get("offset", 9))
    limit = 3

    if not request.user.is_authenticated:
        # Restrict events with age restrictions for anonymous users
        age_filter = Q(age_restriction="")
    else:
        # For authenticated users, calculate age and apply restrictions
        user_age = request.user.age
        if user_age is None and request.user.birthday:
            today = date.today()
            user_age = (
                today.year
                - request.user.birthday.year
                - (
                    (today.month, today.day)
                    < (request.user.birthday.month, request.user.birthday.day)
                )
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
        status="live", forAllDisplay=True, admin_status="active"
    )[offset : offset + limit]

    events_data = []
    for event in more_events:
        events_data.append(
            {
                "eventId": event.eventId,
                "title": event.title,
                "date": event.date.strftime("%Y-%m-%d"),  # Format date as needed
                "host_username": (
                    event.host.username if event.host else "Unknown"
                ),  # Handle case where host might be missing
                "header_photo_url": (
                    event.header_photo.url if event.header_photo else ""
                ),  # Ensure photo URL is included
                "status": event.status,
            }
        )

    has_more = Event.objects.filter(
        status="live", forAllDisplay=True, admin_status="active"
    ).count() > (offset + limit)

    return JsonResponse({"events": events_data, "has_more": has_more})

def toggleFavorite(request, eventId):
    user =  get_object_or_404(UserProfile, user=request.user) if request.user.is_authenticated else None
    event = get_object_or_404(Event, eventId=eventId)
    action = request.POST.get('eventAction')
    
    if user:
        if action == "favoriteEvent":
            user.favorite_events.add(event)
            return JsonResponse({"status": "successfulFavorite", "message": "Event added to favorites."})
        else:
            user.favorite_events.remove(event)
            return JsonResponse({"status": "successfulUnfavorite", "message": "Event removed from favorites."})
    else:
        messages.warning(request, "Please login to favorite events.")
        return redirect("authentication:login")
    
def handleRSVP(request, eventId):
    event = get_object_or_404(Event, eventId=eventId)
    response_data = {}
    
    if request.user.is_authenticated:
        existing_rsvp = RSVPTicket.objects.filter(event=event, email=request.user.email).first()
    else:
        existing_rsvp = None

    if existing_rsvp:
        print("existing rsvp: ", existing_rsvp)
        messages.warning(request, "Your RSVP has already been submitted.")
        response_data = {
            "status": "error",
            "message": "This email has already been submitted!"
        }
        return JsonResponse(response_data)

    # Initialize the form with POST data.
    rsvpForm = RSVPForm(request.POST, user=request.user)
    if rsvpForm.is_valid():
        rsvp_ticket = rsvpForm.save(commit=False)
        existing_rsvp = RSVPTicket.objects.filter(event=event, email=rsvp_ticket.email).first()
        if existing_rsvp:
            messages.warning(request, "This email has already been submitted!")
            response_data = {
                "status": "error",
                "message": "This email has already been submitted! Try a different one."
            }
            return JsonResponse(response_data, status=400)
        # If the event is paid, set the ticket price.
        
        # If the user is authenticated, add them to the guest list.
        if request.user.is_authenticated:
            user_profile = get_object_or_404(UserProfile, user=request.user)
            event.guest_list.add(user_profile.user)
            rsvp_ticket.first_name = request.user.first_name
            rsvp_ticket.last_name = request.user.last_name
            rsvp_ticket.email = request.user.email
            
        rsvp_ticket.event = event
        rsvp_ticket.save()

        guestFirstName = rsvp_ticket.first_name
        guestLastName = rsvp_ticket.last_name
        guestEmail = rsvp_ticket.email
        generateTicket(request, event, request.user if request.user.is_authenticated else None, guestFirstName, guestLastName, guestEmail)
        
        messages.success(request, "You have reserved a spot! Check your email for confirmation.")
        response_data = {
            "status": "success",
            "message": "You have reserved a spot! Check your email for confirmation."
        }
        return JsonResponse(response_data)
    else:
        messages.error(request, "There was an error with your submission.")
        response_data = {
            "status": "error",
            "message": "There was an error with your submission.",
            "errors": rsvpForm.errors,
        }
        return JsonResponse(response_data, status=400)



def eventDetailsView(request, eventId, token=None):
    pageName = "eventDetails"
    event = get_object_or_404(Event, eventId=eventId)
    eventPaidFreeTickets = PaidFreeTicket.objects.filter(event=event)
    
    siteURL = settings.SITE_URL
    link = reverse('core:eventDetails', kwargs={'eventId': eventId})
    eventLink = f"{siteURL}{link}"
    
    # Create RSVP form for Free events
    rsvpForm = RSVPForm(user=request.user) if event.ticketing == "Free" else None
    rsvp_guests = RSVPTicket.objects.filter(event=event, display_on_guestlist=True)
    user = None
    user_friends = None
    user_crews = None
    guest_list = event.guest_list.all()

    if request.user.is_authenticated:
        user = get_object_or_404(UserProfile, user=request.user)
        user_friends = user.friends.all()
        user_crews = user.get_all_crews()

        user_age = request.user.age
        if user_age is None and request.user.birthday:
            today = date.today()
            user_age = (
                today.year
                - request.user.birthday.year
                - (
                    (today.month, today.day)
                    < (request.user.birthday.month, request.user.birthday.day)
                )
            )
            request.user.age = user_age
            request.user.save()
    else:
        # Anonymous users cannot bypass age restrictions
        user_age = None

    isFavoriteEvent = False

    if user and hasattr(user, "favorite_events"):
        isFavoriteEvent = user.favorite_events.filter(eventId=event.eventId).exists()

    if request.method == "POST":
        action = request.POST.get("eventAction")

        if action == "shareEventWithFriend":
            if not request.user.is_authenticated:
                messages.warning(request, "Please login to share this event.")
                return redirect("authentication:login")
            else:
                friend_username = request.POST.get("shareFriendUsername")
                friendUserAccount = get_object_or_404(
                    CustomUser, username=friend_username
                )
                friend = get_object_or_404(UserProfile, user=friendUserAccount)

                myUserAccount = get_object_or_404(
                    CustomUser, username=request.user.username
                )
                user = get_object_or_404(UserProfile, user=myUserAccount)

                shared_event, created = SharedEvent.objects.get_or_create(
                    sender=user, receiver=friend, event=event
                )

                if created:
                    messages.success(request, f"Event shared with {friend}")
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f"user_{friend.user.id}",
                        {
                            "type": "social_update",
                            "data": {
                                "message": "Event shared with friend",
                                "action": "shared_event",
                                "shared_event": {
                                    "event": event.title,
                                    "event_id": str(event.eventId),
                                    "header_photo": event.header_photo.url,
                                    "date": event.date.strftime("%b. %d, %Y"),
                                    "sender": {
                                        "username": shared_event.sender.user.username,
                                    },
                                },
                            },
                        },
                    )
                else:
                    messages.error(request, f"Event already shared with {friend}")
                return redirect("core:eventDetails", eventId=event.eventId)

        elif action == "shareEventWithCrew":
            if not request.user.is_authenticated:
                messages.warning(request, "Please login to share this event.")
                return redirect("authentication:login")
            else:
                crew_id = request.POST.get("shareCrewId")
                crew = get_object_or_404(Crew, crewId=crew_id)

                user = get_object_or_404(UserProfile, user=request.user)

                for member in crew.members.all():
                    SharedEvent.objects.get_or_create(
                        crew=crew,
                        sender=user,
                        receiver=member.user_profile,
                        event=event,
                    )

                messages.success(request, f"Event shared with {crew.name}")
                return redirect("core:eventDetails", eventId=event.eventId)

        elif action == "purchaseForCrew":
            if not request.user.is_authenticated:
                messages.warning(
                    request, "Please login to purchase tickets for a crew."
                )
                return redirect("authentication:login")
            else:
                crew_id = request.POST.get("crewId")
                ticketId = request.POST.get("ticketId")

                return redirect(
                    "eventTickets:crewCheckout", crewId=crew_id, ticketId=ticketId
                )

    

    else:
        return render(
            request,
            "coreApp/event/eventDetails.html",
            {
                "page": pageName,
                "event": event,
                "rsvpForm": rsvpForm,
                "paidFreeTickets": eventPaidFreeTickets,
                "friends": user_friends,
                "crews": user_crews,
                "isFavoriteEvent": isFavoriteEvent,
                "guestList": guest_list,
                "eventLink": eventLink,
            },
        )


def categoryView(request, name):
    category_events = Event.objects.filter(event_type=name)

    if not category_events.exists():
        return render(
            request, "coreApp/category/empty_category.html", {"categoryName": name}
        )

    return render(
        request,
        "coreApp/category/category.html",
        {
            "categoryEvents": category_events,
            "categoryName": name,
            "events": category_events,
        },
    )


def rsvpConfirm(request):
    return render(request, "extras/confirmations/RSVPConfirm.html")


def searchEvents(request):
    search_query = request.GET.get("query", "")
    results = []

    if not request.user.is_authenticated:
        age_filter = Q(age_restriction="")
    else:
        user_age = request.user.age
        if user_age is None and request.user.birthday:
            today = date.today()
            user_age = (
                today.year
                - request.user.birthday.year
                - (
                    (today.month, today.day)
                    < (request.user.birthday.month, request.user.birthday.day)
                )
            )
            request.user.age = user_age
            request.user.save()

        age_filter = Q(age_restriction="")
        if user_age:
            if user_age >= 21:
                age_filter |= Q(age_restriction="21+")
            if user_age >= 18:
                age_filter |= Q(age_restriction="18+")

    if search_query:
        search_events = Event.objects.filter(
            Q(title__icontains=search_query) | Q(event_type__icontains=search_query),
            status="live",
        )

        results = [
            {
                "eventId": event.eventId,
                "title": event.title,
                "date": event.date.strftime("%Y-%m-%d"),  # Format date as needed
                "host_username": (
                    event.host.username if event.host else "Unknown"
                ),  # Handle case where host might be missing
                "header_photo_url": (
                    event.header_photo.url if event.header_photo else ""
                ),  # Ensure photo URL is included
                "status": event.status,
            }
            for event in search_events
        ]

    return JsonResponse({"results": results})


def search_users(request):
    search_query = request.GET.get("query", "").strip()
    results = []

    if search_query:
        # Subqueries to check friend request status and friendship
        sent_requests = FriendRequest.objects.filter(
            sender=request.user,
            receiver=OuterRef("pk"),
            status__in=["pending", "accepted"],
        )
        received_requests = FriendRequest.objects.filter(
            sender=OuterRef("pk"), receiver=request.user, status="pending"
        )
        # Assuming 'accepted' status indicates friendship
        friends = FriendRequest.objects.filter(
            Q(sender=request.user, receiver=OuterRef("pk"), status="accepted")
            | Q(sender=OuterRef("pk"), receiver=request.user, status="accepted")
        )

        users = (
            CustomUser.objects.filter(
                Q(username__icontains=search_query)
                | Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
            )
            .exclude(id=request.user.id)
            .distinct()[:10]
            .annotate(
                has_sent_friend_request=Exists(sent_requests), is_friend=Exists(friends)
            )
        )

        results = [
            {
                "username": user.username,
                "display_name": f"{user.first_name} {user.last_name}".strip()
                or user.username,
                "profile_photo_url": (
                    user.user_profile.profile_photo.url
                    if hasattr(user, "user_profile") and user.user_profile.profile_photo
                    else "/static/images/default_profile.png"
                ),
                "has_sent_friend_request": user.has_sent_friend_request,
                "is_friend": user.is_friend,
            }
            for user in users
        ]

    return JsonResponse({"results": results})


@login_required
@require_POST
def send_connect_request(request):
    action = request.POST.get("action")
    username = request.POST.get("socketUsername")

    if action == "send_request":
        try:
            to_user = CustomUser.objects.get(username=username)

            if to_user == request.user:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "You cannot send a friend request to yourself.",
                    },
                    status=400,
                )

            # Attempt to get or create the FriendRequest
            created = FriendRequest.objects.get_or_create(
                sender=request.user, receiver=to_user, defaults={"status": "pending"}
            )

            if created:
                return JsonResponse(
                    {"status": "success", "message": "Friend request sent."}
                )
            else:
                return JsonResponse(
                    {"status": "error", "message": "Friend request already sent."},
                    status=400,
                )

        except CustomUser.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "User not found."}, status=404
            )

    return JsonResponse({"status": "error", "message": "Invalid action."}, status=400)


def track_visitor(request):
    if request.method == "GET":
        # Retrieve the visitor's IP address
        ip_address = get_client_ip(request)

        # Check if the IP address is already recorded
        visitor, created = Visitor.objects.get_or_create(
            ip_address=ip_address, defaults={"first_visit": now()}
        )

        # Prepare a JSON response
        response_data = {
            "new_visitor": created,
            "ip_address": visitor.ip_address,
            "first_visit": visitor.first_visit,
        }
        return JsonResponse(response_data)
    else:
        return JsonResponse({"error": "Invalid request method"}, status=400)


def get_client_ip(request):
    """Get the client's IP address from the request object."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")

    return ip
