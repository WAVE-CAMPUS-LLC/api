from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
import random
from django.db.models import Count

from eventManagementApp.models import Event, EventTicket


# Create your views here.
def indexView(request):
    pageName = "home"
    return render(request, "coreApp/index.html", {"page": pageName})


def exploreView(request):
    """
    The `exploreView` function in Python retrieves initial events, trending events, and trending
    categories for display on an explore page in a web application.
    
    :param request: The `exploreView` function is a Django view that renders an "explore.html" template
    with various context data. Here's a breakdown of the parameters used in the function:
    :return: The `exploreView` function returns a rendered template named "coreApp/explore.html" with
    the following context data:
    - "page": containing the value "explore"
    - "events": containing the initial 6 events loaded from the database
    - "trending_events": containing the trending events with a status of "live" ordered by date
    - "exploreCategoryChoices": a
    """
    pageName = "explore"

    # Load initial 6 events
    initial_events = Event.objects.all()[:7]
    trending_events = Event.objects.filter(status="live").order_by("date")[:3]

    trending_categories = (
        Event.objects.values("event_type")
        .annotate(event_count=Count("event_type"))
        .order_by("-event_count")[:4]  
    )
    
    
    trending_category_choices = []
    for category in trending_categories:
        event_type = category["event_type"]
        display_name = dict(Event.EXPLORE_TYPE_CHOICES).get(event_type, event_type)
        trending_category_choices.append((event_type, display_name))

    if len(trending_category_choices) < 4:
        remaining_choices = list(set(Event.EXPLORE_TYPE_CHOICES) - set(trending_category_choices))
        additional_choices = random.sample(remaining_choices, 4 - len(trending_category_choices))
        trending_category_choices += additional_choices
        
    explore_category_images = Event.EXPLORE_CATEGORY_TYPE_IMAGES

    return render(
        request,
        "coreApp/explore.html",
        {
            "page": pageName,
            "events": initial_events,
            "trending_events": trending_events,
            "exploreCategoryChoices": trending_category_choices,
            "exploreCategoryImages": explore_category_images,
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

    more_events = Event.objects.all()[offset : offset + limit]
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

    has_more = Event.objects.count() > (offset + limit)

    return JsonResponse({"events": events_data, "has_more": has_more})


def eventDetailsView(request, eventId):
    pageName = "eventDetails"
    event = get_object_or_404(Event, eventId=eventId)
    eventTickets = EventTicket.objects.filter(event=event)

    return render(
        request,
        "coreApp/event/eventDetails.html",
        {
            "page": pageName,
            "event": event,
            "eventTickets": eventTickets,
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
