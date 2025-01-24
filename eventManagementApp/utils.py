# utils.py or a similar utility module
from django.contrib import messages
from django.shortcuts import redirect
from .models import EventPrivacy
from collegeManagementApp.models import CollegeEventLink

def set_event_privacy(event, user_profile, organization_membership, request):
    privacy_actions = {
        "Discoverable": {
            "display_on_explore": True,
            "require_invitation": False,
            "restricted_college": None,
            "restricted_organization": None,
            "additional_actions": []
        },
        "Invite Only": {
            "display_on_explore": False,
            "require_invitation": True,
            "restricted_college": None,
            "restricted_organization": None,
            "additional_actions": [
                lambda evt: setattr(evt, 'ticketing', 'Invite Required')
            ]
        },
        "Private (College)": {
            "display_on_explore": False,
            "require_invitation": False,
            "restricted_college": user_profile.college if user_profile.college else None,
            "restricted_organization": None,
            "additional_actions": [
                lambda evt: setattr(evt, 'display_event_on_college', True),
                lambda evt: CollegeEventLink.objects.get_or_create(
                    college=user_profile.college, event=evt
                ) if user_profile.college else None
            ]
        },
        "Private (Organization)": {
            "display_on_explore": False,
            "require_invitation": False,
            "restricted_college": None,
            "restricted_organization": organization_membership.organization if organization_membership else None,
            "additional_actions": []
        }
    }

    privacy_setting = privacy_actions.get(event.privacy)

    if not privacy_setting:
        messages.error(request, "Invalid privacy setting selected.")
        return False

    # Handle required checks for specific privacy types
    if event.privacy == "Private (College)" and not user_profile.college:
        messages.error(request, "You must be part of a college to create a college event.")
        return False

    # Execute additional actions if any
    for action in privacy_setting["additional_actions"]:
        if action:
            action(event)

    # Create the EventPrivacy object
    EventPrivacy.objects.create(
        event=event,
        display_on_explore=privacy_setting["display_on_explore"],
        require_invitation=privacy_setting["require_invitation"],
        restricted_college=privacy_setting["restricted_college"],
        restricted_organization=privacy_setting["restricted_organization"],
    )

    return True
