from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
import random
from django.db.models import Count

from eventManagementApp.models import (
    Event,
    RSVPTicket,
    EventPrivacy,
    InviteEventOption,
)
from accountManagementApp.models import UserProfile
from .forms import RSVPForm
from collegeManagementApp.models import OrganizationMembership


# Create your views here.
def indexView(request):
    pageName = "home"
    return render(request, "coreApp/index.html", {"page": pageName})


def exploreView(request):
    pageName = "explore"

    # Load initial 6 events
    initial_events = Event.objects.filter(status="live", privacy="Discoverable")[:7]
    trending_events = Event.objects.filter(
        status="live", privacy="Discoverable"
    ).order_by("date")[:3]
    
    # Retrieve the user profile and invited events
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        invited_events = user_profile.invited_events.filter(status="live")
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
        Event.objects.filter(status="live", privacy="Discoverable")
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

    return render(
        request,
        "coreApp/explore.html",
        {
            "page": pageName,
            "events": initial_events,
            "trending_events": trending_events,
            "exploreCategoryChoices": trending_category_choices,
            "invited_events_with_tokens": invited_events_with_tokens,
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
    offset = int(request.GET.get("offset", 7))
    limit = 3

    more_events = Event.objects.filter(status="live", privacy="Discoverable")[
        offset : offset + limit
    ]
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

    has_more = Event.objects.filter(status="live", privacy="Discoverable").count() > (
        offset + limit
    )

    return JsonResponse({"events": events_data, "has_more": has_more})


def eventDetailsView(request, eventId, token=None):
    pageName = "eventDetails"
    event = get_object_or_404(Event, eventId=eventId)
    eventprivacy = EventPrivacy.objects.get(event=event)
    
    rsvpForm = RSVPForm() if event.ticketing == "RSVP Required" else None
    
    if request.method == "POST":
        action = request.POST.get("eventAction")
        
        if action == "RSVP":
            rsvpForm = RSVPForm(request.POST)
            if rsvpForm.is_valid():
                rsvp_ticket = rsvpForm.save(commit=False)
                rsvp_ticket.event = event 
                rsvp_ticket.save()
                return redirect("core:rsvpConfirm")

    if eventprivacy.require_invitation:
        if token:
            invitation = get_object_or_404(InviteEventOption, token=token)
            return render(
                request,
                "coreApp/event/eventDetails.html",
                {
                    "page": pageName,
                    "event": event,
                    "eventPrivacy": eventprivacy,
                    "rsvpForm": rsvpForm,
                },
            )
        else:
            return render(
                request,
                "extras/invalid/eventInvalid.html",
                {
                    "page": pageName,
                    "event": event,
                    "eventPrivacy": eventprivacy
                },
            )

    elif eventprivacy.restricted_college:
        if request.user.user_profile.college == eventprivacy.restricted_college:
            return render(
                request,
                "coreApp/event/eventDetails.html",
                {
                    "page": pageName,
                    "event": event,
                    "rsvpForm": rsvpForm,
                },
            )
        else:
            return render(
                request,
                "extras/invalid/eventCollegePrivacy.html",
                {
                    "page": pageName,
                    "event": event,
                    "eventPrivacy": eventprivacy,
                },
            )
            
    elif eventprivacy.restricted_organization:
        userOrgRelation = OrganizationMembership.objects.filter(
            user=request.user, organization=eventprivacy.restricted_organization
        )
        
        if userOrgRelation.exists():
            return render(
                request,
                "coreApp/event/eventDetails.html",
                {
                    "page": pageName,
                    "event": event,
                    "rsvpForm": rsvpForm,
                },
            )
        else:
            return render(
                request,
                "extras/invalid/eventOrganizationPrivacy.html",
                {
                    "page": pageName,
                    "event": event,
                    "eventPrivacy": eventprivacy,
                },
            )

    else:
        return render(
            request,
            "coreApp/event/eventDetails.html",
            {
                "page": pageName,
                "event": event,
                "rsvpForm": rsvpForm,
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