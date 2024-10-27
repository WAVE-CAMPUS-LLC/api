from datetime import datetime
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail
from wave_v1.decorators import group_required
from django.urls import reverse


from accountManagementApp.models import UserProfile
from collegeManagementApp.models import Organization, OrganizationMembership
from .forms import EventTicketForm, HostApplicationForm, EventForm, InvitationForm
from .models import (
    EventTicket,
    EventType,
    HostApplication,
    Event,
    EventPrivacy,
    InviteEventOption,
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
    live_event = Event.objects.filter(host=request.user, status="live")
    incomplete_event = Event.objects.filter(host=request.user, status="incomplete")

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

        if "displayOnCollege" in request.POST:
            event_to_update = get_object_or_404(
                Event, eventId=event_id, host=request.user
            )
            event_to_update.display_event_on_college = (
                request.POST["displayOnCollege"] == "True"
            )  # Check for 'true'
            event_to_update.save()
            return redirect("eventManagement:hostPortal")
    return render(
        request,
        "eventManagementApp/host/hostPortal.html",
        {
            "liveEvents": live_event,
            "incompleteEvents": incomplete_event,
            "isInCollege": is_in_college,
        },
    )


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
    privacy_choices = Event.PRIVACY_CHOICES

    if request.method == "POST":
        eventForm = EventForm(request.POST, request.FILES, instance=event)
        go_live = request.POST.get("goLiveInput") == "1"

        if eventForm.is_valid():
            event = eventForm.save(commit=False)
            event.event_type = request.POST.get("event_type")

            if go_live:
                event_status = "live"
                event.status = event_status

                messages.success(request, "Event is live!")

                user_profile = event.host.user_profile
                organization_membership = OrganizationMembership.objects.filter(
                    user=event.host
                ).first()

                if event.privacy == "Discoverable":
                    event_privacy = EventPrivacy.objects.create(
                        event=event,
                        display_on_explore=True,
                        require_invitation=False,
                        restricted_college=None,
                        restricted_organization=None,
                    )
                    event_privacy.save()

                elif event.privacy == "Invite Only":
                    event_privacy = EventPrivacy.objects.create(
                        event=event,
                        display_on_explore=False,
                        require_invitation=True,
                        restricted_college=None,
                        restricted_organization=None,
                    )
                    event.ticketing = "Invite Required"
                    event_privacy.save()

                elif event.privacy == "Private (College)":
                    event_privacy = EventPrivacy.objects.create(
                        event=event,
                        display_on_explore=False,
                        require_invitation=False,
                        restricted_college=event.host.user_profile.college,
                        restricted_organization=None,
                    )
                    event.display_event_on_college = True
                    event_privacy.save()

                elif (
                    event.privacy == "Private (Organization)"
                    and organization_membership
                ):
                    event_privacy = EventPrivacy.objects.create(
                        event=event,
                        display_on_explore=False,
                        require_invitation=False,
                        restricted_college=None,
                        restricted_organization=organization_membership.organization,
                    )
                    event_privacy.save()

                event.save()
                return redirect("eventManagement:eventManagement", eventId=eventId)

            else:
                event.save()

            return redirect("eventManagement:eventManagement", eventId=eventId)
    else:
        eventForm = EventForm(instance=event)

    return render(
        request,
        "eventManagementApp/host/eventCreationProcess.html",
        {
            "event": event,
            "eventForm": eventForm,
            "eventTypeChoices": event_type_choices,
            "privacyChoices": privacy_choices,
        },
    )


@login_required
@group_required("Host")
def save_event_progress(request, eventId):
    if request.method == "POST":
        # Retrieve the event object
        event = get_object_or_404(
            Event, eventId=eventId
        )  # Use `id` to match your model field

        # Handling all relevant fields
        event.status = request.POST.get("status", "incomplete")
        event.title = request.POST.get("title", "")
        event.event_type = request.POST.get("event_type", "")

        # Handling date and time fields
        date_str = request.POST.get("date", "")
        start_time_str = request.POST.get("start_time", "")
        end_time_str = request.POST.get("end_time", "")

        if date_str:
            event.date = datetime.strptime(date_str, "%Y-%m-%d").date()

        if start_time_str:
            event.start_time = datetime.strptime(start_time_str, "%H:%M").time()

        if end_time_str:
            event.end_time = datetime.strptime(end_time_str, "%H:%M").time()

        event.description = request.POST.get("description", "")
        event.privacy = request.POST.get("privacy", "")
        event.country = request.POST.get("country", "")
        event.building_name = request.POST.get("building_name", "")
        event.street_address = request.POST.get("street_address", "")
        event.apt_suite_unit = request.POST.get("apt_suite_unit", "")
        event.city = request.POST.get("city", "")
        event.state = request.POST.get("state", "")
        event.zip_code = request.POST.get("zip_code", "")
        event.contact_email = request.POST.get("contact_email", "")
        event.contact_phone = request.POST.get("contact_phone", "")
        event.contact_website = request.POST.get("contact_website", "")
        event.contact_instagram = request.POST.get("contact_instagram", "")
        event.header_photo = request.FILES.get("header_photo", None)
        event.body_photo_one = request.FILES.get("body_photo_one", None)
        event.body_photo_two = request.FILES.get("body_photo_two", None)
        event.body_photo_three = request.FILES.get("body_photo_three", None)
        event.body_photo_four = request.FILES.get("body_photo_four", None)
        event.body_photo_five = request.FILES.get("body_photo_five", None)

        event.save()  # Save changes to the database

        return JsonResponse({"success": True})

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
@group_required("Host")
def eventManagement(request, eventId):
    event = get_object_or_404(Event, eventId=eventId)
    user_profile = UserProfile.objects.get(user=request.user)
    is_in_college = user_profile.college is not None
    event_privacy = EventPrivacy.objects.get(event=event)

    if request.method == "POST":
        action = request.POST.get("eventAction")
        invitationForm = InvitationForm(request.POST)

        if action == "deleteEvent":
            event.delete()
            return redirect("eventManagement:hostPortal")

        if "displayOnCollege" in request.POST:
            event_to_update = get_object_or_404(
                Event, eventId=event.eventId, host=request.user
            )
            event_to_update.display_event_on_college = (
                request.POST["displayOnCollege"] == "True"
            )  # Check for 'true'
            event_to_update.save()
            return redirect("eventManagement:eventManagement", eventId=eventId)

        if action == "sendInvites" and invitationForm.is_valid():
            emails = invitationForm.cleaned_data["invite_emails"]
            subject = invitationForm.cleaned_data["invite_subject"]
            message = invitationForm.cleaned_data["invite_message"]
            emailList = [email.strip() for email in emails.split(",")]

            for email in emailList:
                invitation = InviteEventOption(event=event, email=email)
                # invitation.generate_token()
                invitation.save()
                print(invitation.token)

                invitation_link = request.build_absolute_uri(
                    reverse(
                        "core:eventDetails_withToken",
                        kwargs={
                            "eventId": str(eventId),
                            "token": invitation.token,
                        },
                    )
                )
                emailMessageHtml = render_to_string(
                    "emailTemplates/eventManagementApp/host/inviteAttendees.html",
                    {"body": message, "invitationLink":invitation_link},
                )
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=None,
                    fail_silently=False,
                    recipient_list=[email],
                    html_message=emailMessageHtml,
                )
            return redirect("eventManagement:eventManagement", eventId=eventId)

    else:
        invitationForm = InvitationForm()

    return render(
        request,
        "eventManagementApp/host/eventManagement.html",
        {
            "event": event,
            "isInCollege": is_in_college,
            "userProfile": user_profile,
            "eventPrivacy": event_privacy,
            "invitationForm": invitationForm,
        },
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
