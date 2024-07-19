from django.shortcuts import get_object_or_404, render

from eventManagementApp.models import Event


# Create your views here.
def indexView(request):
    pageName = "home"
    return render(request, "coreApp/index.html", {"page": pageName})


def exploreView(request):
    pageName = "explore"
    events = Event.objects.all()
    return render(request, "coreApp/explore.html", {"page": pageName, "events": events})


def eventDetailsView(request, eventId):
    pageName = "eventDetails"
    event = get_object_or_404(Event, eventId=eventId)
    
    body_photos = [
        event.body_photo_one.url if event.body_photo_one else None, 
        event.body_photo_two.url if event.body_photo_two else None,
        event.body_photo_three.url if event.body_photo_three else None,
        event.body_photo_four.url if event.body_photo_four else None,
        event.body_photo_five.url if event.body_photo_five else None,
    ]
    
    body_photos = [photo for photo in body_photos if photo]
    
    return render(
        request, "coreApp/event/eventDetails.html", {"page": pageName, "event": event, "body_photos":body_photos}
    )
