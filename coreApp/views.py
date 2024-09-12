from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse

from eventManagementApp.models import Event, EventTicket


# Create your views here.
def indexView(request):
    pageName = "home"
    return render(request, "coreApp/index.html", {"page": pageName})


def exploreView(request):
    pageName = "explore"
    # events = Event.objects.all()

    # Load initial 6 events
    initial_events = Event.objects.all()[:7]
    trending_events = Event.objects.filter(status="live").order_by("date")[:3]

    explore_category_choices = Event.EXPLORE_TYPE_CHOICES
    explore_category_images = Event.EXPLORE_CATEGORY_TYPE_IMAGES

    return render(
        request,
        "coreApp/explore.html",
        {
            "page": pageName,
            "events": initial_events,
            "trending_events": trending_events,
            "exploreCategoryChoices": explore_category_choices,
            "exploreCategoryImages": explore_category_images,
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
