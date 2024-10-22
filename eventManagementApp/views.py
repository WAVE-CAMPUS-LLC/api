from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from wave_v1.decorators import group_required


from accountManagementApp.models import UserProfile
from .forms import EventTicketForm, HostApplicationForm, EventForm
from .models import (
    EventTicket,
    EventType,
    HostApplication,
    Event,
)


# Create your views here.
def hostView(request):
    pageName = "Host Event"
    return render(
        request, "eventManagementApp/host/hostHome.html", {"pageName": pageName}
    )


def hostApplyView(request):
    """
    The `hostApplyView` function handles the submission of a host application form in a Django web
    application.

    :param request: The `request` parameter in the `hostApplyView` function is an object that contains
    information about the current HTTP request. It includes details such as the request method (GET,
    POST, etc.), request data (POST data, query parameters), user session information, and more. In this
    function,
    :return: The `hostApplyView` function returns a rendered HTML template named "hostApplication.html"
    along with a form object. The form object is either a new instance of `HostApplicationForm` if the
    request method is not POST, or a form populated with the POST data if the request method is POST and
    the form is valid. If the form is valid, the function also saves the form data to
    """
    if request.method == "POST":
        form = HostApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.save()
            event_types = form.cleaned_data["eventTypes"]
            event_type_objs = [
                EventType.objects.get_or_create(name=et)[0] for et in event_types
            ]
            application.eventTypes.set(event_type_objs)
            return redirect("eventManagement:hostHome")
    else:
        form = HostApplicationForm()
    return render(
        request, "eventManagementApp/host/hostApplication.html", {"form": form}
    )


@login_required
@group_required("Host")
def hostPortalView(request):
    event = Event.objects.filter(host=request.user)
    
    user_profile = UserProfile.objects.get(user=request.user)
    is_in_college = user_profile.college is not None

    if request.method == "POST":
        action = request.POST.get("eventAction")
        event_id = request.POST.get("event_id")

        if action == "deleteEvent" and event_id:
            event_to_delete = get_object_or_404(
                Event, eventId=event_id, host=request.user
            )
            event_to_delete.delete()
            return redirect("eventManagement:hostPortal")
        
        if 'displayOnCollege' in request.POST:
            event_to_update = get_object_or_404(Event, eventId=event_id, host=request.user)
            event_to_update.display_event_on_college = request.POST['displayOnCollege'] == 'True'  # Check for 'true'
            event_to_update.save()
            return redirect("eventManagement:hostPortal")
    return render(request, "eventManagementApp/host/hostPortal.html", {"events": event, "isInCollege": is_in_college})


@login_required
@group_required("Host")
def hostGuideView(request):
    return render(request, "eventManagementApp/host/hostGuide.html")


@login_required
@group_required("Host")
def hostCreateEvent(request):
    return render(request, "eventManagementApp/host/createEvent.html")


@login_required
@group_required("Host")
def hostCreateEventGenerator(request):
    event = Event.objects.create(host=request.user)

    return redirect("eventManagement:eventCreationProcess", eventId=event.eventId)


@login_required
@group_required("Host")
def eventCreationProcess(request, eventId):
    event = get_object_or_404(Event, eventId=eventId)
    event_type_choices = Event.EVENT_TYPE_CHOICES
    
    

    if request.method == "POST":
        eventForm = EventForm(request.POST, request.FILES, instance=event)
        go_live = request.POST.get("goLiveInput") == "1"

        if eventForm.is_valid():
            event = eventForm.save(commit=False)
            event.event_type = request.POST.get("event_type")

            if go_live:
                event_status = "live"
                event.status = event_status
                event.save()
                messages.success(request, "Event is live!")

            else:
                event.save()

            return redirect("eventManagement:eventOverview", eventId=eventId)
    else:
        eventForm = EventForm()

    return render(
        request,
        "eventManagementApp/host/eventCreationProcess.html",
        {
            "event": event,
            "eventForm": eventForm,
            "eventTypeChoices": event_type_choices,
        },
    )


@login_required
@group_required("Host")
def eventCreatedOverview(request, eventId):
    event = get_object_or_404(Event, eventId=eventId)
    if request.method == "POST":
        action = request.POST.get("eventAction")

        if action == "deleteEvent":
            event.delete()
            return redirect("eventManagement:hostPortal")
    return render(
        request, "eventManagementApp/host/eventPreview.html", {"event": event}
    )


@login_required
@group_required("Host")
def eventTicketingOverview(request, eventId):
    event = get_object_or_404(Event, eventId=eventId)
    eventTicket = EventTicket.objects.filter(event=event)
    eventTicketForm = EventTicketForm(request.POST)

    if request.method == "POST":
        if eventTicketForm.is_valid():
            new_ticket = eventTicketForm.save(commit=False)
            new_ticket.event = event
            new_ticket.save()
            
            return redirect("eventManagement:ticketingOverview", eventId=eventId)
    else:
        eventTicketForm = EventTicketForm()

    return render(
        request,
        "eventManagementApp/host/event/ticketing/ticketingOverview.html",
        {
            "event": event,
            "eventTickets": eventTicket,
            "eventTicketForm": eventTicketForm,
        },
    )
