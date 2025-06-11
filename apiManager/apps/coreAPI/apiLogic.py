from typing import Optional
from channels.db import database_sync_to_async
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
import bleach

# Django imports
from coreApp.forms import RSVPForm
from eventManagementApp.models import Event
from accountManagementApp.models import UserProfile
from eventTicketsApp.models import RSVPTicket, Ticket
from eventTicketsApp.views import generateTicket
from socialApp.models import Crew, CrewMember

# API Manager imports
from .serializers import ExplorePageEvent, EventDetailsSerializer, RSVPInformation
from apiManager.dependencies import get_current_user
from authenticationApp.models import CustomUser
from uuid import UUID
from .version_middleware import VersionCheckMiddleware


router = APIRouter()


@router.get("/ping")
async def ping():
    return {"message": "Core API is running!"}


@router.get("/events/preview")
async def get_events_preview():
    """
    API endpoint to retrieve a preview of events for the explore page.
    """
    print("[get_events_preview API] Function called")

    @database_sync_to_async
    def get_events_preview_data():
        events_list = []
        # Get 3 random events using order_by('?')
        for event in Event.objects.order_by("?")[:3]:
            header_photo_url = event.header_photo.url if event.header_photo else None
            events_list.append(
                {
                    "eventId": str(event.eventId),  # Convert UUID to string
                    "title": event.title,
                    "date": event.date,
                    "header_photo": header_photo_url,
                    "event_type": event.event_type,
                    "state": event.state,
                    "city": event.city,
                    "ticketing": str(event.ticketing),  # Ensure it's a string
                    "forAllDisplay": bool(event.forAllDisplay),  # Ensure it's a boolean
                    "forCollegesDisplay": bool(
                        event.forCollegesDisplay
                    ),  # Ensure it's a boolean
                }
            )
        return events_list

    events_data = await get_events_preview_data()
    events = [ExplorePageEvent(**event_data) for event_data in events_data]
    response = {"events": events}

    return response


@router.get("/events")
async def get_events():
    """
    API endpoint to retrieve events for the explore page.
    """
    print("[get_events API] Function called")

    @database_sync_to_async
    def get_events_data():
        events_list = []
        for event in Event.objects.all():
            header_photo_url = event.header_photo.url if event.header_photo else None
            events_list.append(
                {
                    "eventId": str(event.eventId),  # Convert UUID to string
                    "title": event.title,
                    "date": event.date,
                    "header_photo": header_photo_url,
                    "event_type": event.event_type,
                    "state": event.state,
                    "city": event.city,
                    "ticketing": str(event.ticketing),  # Ensure it's a string
                    "forAllDisplay": bool(event.forAllDisplay),  # Ensure it's a boolean
                    "forCollegesDisplay": bool(
                        event.forCollegesDisplay
                    ),  # Ensure it's a boolean
                }
            )
        print(f"[get_events API] Retrieved {len(events_list)} events from database")
        return events_list

    # Get the data and convert to Pydantic models
    events_data = await get_events_data()
    events = [ExplorePageEvent(**event_data) for event_data in events_data]

    response = {"events": events}
    print(f"[get_events API] Returning {len(events)} events in response")
    return response


@router.get("/categories")
async def get_categories():
    """
    API endpoint to retrieve all event categories from the EXPLORE_TYPE_CHOICES.
    """
    print("[get_categories API] Function called")

    @database_sync_to_async
    def get_categories_data():
        # Return the categories from the Event model's EXPLORE_TYPE_CHOICES
        categories = [
            {"value": value, "label": label}
            for value, label in Event.EXPLORE_TYPE_CHOICES
        ]
        print(f"[get_categories API] Retrieved {len(categories)} categories")
        return categories

    categories = await get_categories_data()
    response = {"categories": categories}
    print(f"[get_categories API] Returning response with {len(categories)} categories")
    return response


@router.get("/event/{eventId}")
async def get_event_details(eventId: str):
    """
    API endpoint to retrieve details of a specific event.
    """
    print(f"[get_event_details API] Function called with eventId: {eventId}")

    @database_sync_to_async
    def get_event_data(eventId):
        try:
            event = Event.objects.get(eventId=eventId)
            header_photo_url = event.header_photo.url if event.header_photo else None
            body_photo_one_url = (
                event.body_photo_one.url if event.body_photo_one else None
            )
            body_photo_two_url = (
                event.body_photo_two.url if event.body_photo_two else None
            )
            body_photo_three_url = (
                event.body_photo_three.url if event.body_photo_three else None
            )
            body_photo_four_url = (
                event.body_photo_four.url if event.body_photo_four else None
            )
            body_photo_five_url = (
                event.body_photo_five.url if event.body_photo_five else None
            )

            # Get host profile information
            host_profile = (
                event.host.user_profile if hasattr(event.host, "user_profile") else None
            )
            host_data = {
                "id": str(event.host.id),
                "username": event.host.username,
                "first_name": event.host.first_name,
                "last_name": event.host.last_name,
                "profilePhoto": (
                    host_profile.profile_photo.url
                    if host_profile and host_profile.profile_photo
                    else None
                ),
                "isCampusManager": (
                    host_profile.is_campus_manager
                    if host_profile and hasattr(host_profile, "is_campus_manager")
                    else False
                ),
            }

            # Check for guest list
            guest_list = []
            if event.guest_list.exists():
                guest_list = list(
                    event.guest_list.all().values(
                        "id", "username", "first_name", "last_name"
                    )
                )

            # Check for favorite status (default to False since we don't have user context here)
            is_favorite = False

            # Check for RSVP requirement
            rsvp_required = False  # Default value, adjust based on your model

            # Check for paid/free tickets
            paid_free_tickets = []  # Default value, adjust based on your model

            # Sanitize HTML in the description to prevent XSS attacks
            try:
                # Import CSS sanitizer if it exists (in newer versions of bleach)
                css_sanitizer = None
                try:
                    from bleach.css_sanitizer import CSSSanitizer

                    allowed_css_properties = [
                        "color",
                        "font-weight",
                        "text-align",
                        "font-style",
                        "text-decoration",
                    ]
                    css_sanitizer = CSSSanitizer(
                        allowed_css_properties=allowed_css_properties
                    )
                except ImportError:
                    print(
                        "[get_event_details API] CSSSanitizer not available, using basic sanitization"
                    )

                # Clean the HTML with appropriate parameters
                if css_sanitizer:
                    sanitized_description = bleach.clean(
                        event.description,
                        tags=[
                            "p",
                            "br",
                            "strong",
                            "em",
                            "u",
                            "h1",
                            "h2",
                            "h3",
                            "h4",
                            "h5",
                            "h6",
                            "ol",
                            "ul",
                            "li",
                            "b",
                            "i",
                        ],
                        attributes={"*": ["class", "style"]},
                        css_sanitizer=css_sanitizer,
                        strip=True,
                    )
                else:
                    # Fallback to basic sanitization without CSS sanitizer
                    sanitized_description = bleach.clean(
                        event.description,
                        tags=[
                            "p",
                            "br",
                            "strong",
                            "em",
                            "u",
                            "h1",
                            "h2",
                            "h3",
                            "h4",
                            "h5",
                            "h6",
                            "ol",
                            "ul",
                            "li",
                            "b",
                            "i",
                        ],
                        attributes={
                            "*": ["class"]
                        },  # Allow class but not style without CSS sanitizer
                        strip=True,
                    )
            except Exception as e:
                print(f"[get_event_details API] Error sanitizing description: {str(e)}")
                # Fallback to a more basic sanitization if full sanitization fails
                sanitized_description = bleach.clean(event.description, strip=True)

            # Collect all fields that actually exist in the Event model
            return {
                "eventId": str(event.eventId),
                "title": event.title,
                "description": sanitized_description,
                "date": event.date,
                "header_photo": header_photo_url,
                "building_name": event.building_name,
                "street": event.street,
                "apt_suite_unit": event.apt_suite_unit,
                "city": event.city,
                "state": event.state,
                "zip_code": event.zip_code,
                "hide_address": bool(event.hide_address),
                "ticketing": str(event.ticketing),
                "start_time": str(event.start_time),
                "end_time": str(event.end_time),
                "age_restriction": event.age_restriction,
                "event_type": event.event_type,
                "status": event.status,
                "country": event.country,
                "body_photo_one": body_photo_one_url,
                "body_photo_two": body_photo_two_url,
                "body_photo_three": body_photo_three_url,
                "body_photo_four": body_photo_four_url,
                "body_photo_five": body_photo_five_url,
                "host": host_data,
                "guestList": guest_list,
                "isFavoriteEvent": is_favorite,
                "rsvpFormRequired": rsvp_required,
                "paidFreeTickets": paid_free_tickets,
                "crew_discount": bool(event.crew_discount),
                "crew_discount_percentage": event.crew_discount_percentage,
                "minimum_crew_size": event.minimum_crew_size,
                "coupons_activated": bool(event.couponsActivated),
            }
        except Event.DoesNotExist:
            print(f"[get_event_details API] Event not found with ID: {eventId}")
            return None

    event_data = await get_event_data(eventId)
    if event_data is None:
        raise HTTPException(status_code=404, detail="Event not found")

    print(
        f"[get_event_details API] Returning details for event: {event_data.get('title')}"
    )

    return {"event": event_data}


@router.get("/event/{eventId}/host_profile")
async def get_event_host_profile(eventId: str):
    """
    API endpoint to retrieve the host profile for a specific event.
    """
    print(f"[get_event_host_profile API] Function called with eventId: {eventId}")

    @database_sync_to_async
    def get_host_profile(eventId):
        try:
            event = Event.objects.get(eventId=eventId)
            host_profile = (
                event.host.user_profile
            )  # Assuming this is a ForeignKey to UserProfile
            return {
                "profile_photo": (
                    host_profile.profile_photo.url
                    if host_profile.profile_photo
                    else None
                ),
                "first_name": host_profile.user.first_name,
                "last_name": host_profile.user.last_name,
                "id": str(host_profile.user.id),
                "user_id": str(host_profile.user.user_id),
                "username": host_profile.user.username,
            }
        except Event.DoesNotExist:
            print(f"[get_event_host_profile API] Event not found with ID: {eventId}")
            return None

    host_data = await get_host_profile(eventId)
    if host_data is None:
        raise HTTPException(status_code=404, detail="Event not found")

    print(
        f"[get_event_host_profile API] Returning host profile for: {host_data.get('first_name')} {host_data.get('last_name')}"
    )
    return {"host_profile": host_data}


@router.get("/event/{eventId}/guests")
async def get_event_guests(eventId: str):
    """
    API endpoint to retrieve guests for a specific event.
    """
    print(f"[get_event_guests API] Function called with eventId: {eventId}")

    @database_sync_to_async
    def get_guests_data(eventId):
        try:
            event = Event.objects.get(eventId=eventId)
            guests = (
                event.guest_list.all()
            )  # Assuming guests is a related name for the ManyToMany field
            guest_photos = [
                guest.user_profile.profile_photo for guest in guests
            ]  # Adjust according to your User model
            print(
                f"[get_event_guests API] Retrieved {len(guest_photos)} guests for event"
            )
            return guest_photos
        except Event.DoesNotExist:
            print(f"[get_event_guests API] Event not found with ID: {eventId}")
            return None

    guests_data = await get_guests_data(eventId)
    if guests_data is None:
        raise HTTPException(status_code=404, detail="Event not found")

    return {"guests": guests_data}


@router.post("/event/{eventId}/toggleFavorite")
async def toggleFavorite(eventId: str, user_id: int = Depends(get_current_user)):
    """
    API endpoint toggling a favorite on an event
    """
    print(
        f"[toggleFavorite API] Function called with eventId: {eventId}, user_id: {user_id}"
    )

    @database_sync_to_async
    def toggle_fav_event(eventId, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            event = Event.objects.get(eventId=eventId)
            user_profile = UserProfile.objects.get(user=user)
            if event in user_profile.favorite_events.all():
                user_profile.favorite_events.remove(event)
                print(
                    f"[toggleFavorite API] Removed event {event.title} from favorites for user {user.username}"
                )
            else:
                user_profile.favorite_events.add(event)
                print(
                    f"[toggleFavorite API] Added event {event.title} to favorites for user {user.username}"
                )
            user_profile.save()
            return True
        except (
            CustomUser.DoesNotExist or Event.DoesNotExist or UserProfile.DoesNotExist
        ):
            print(
                f"[toggleFavorite API] Error: Could not find user, event, or user profile"
            )
            return False

    success = await toggle_fav_event(eventId, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Could not favorite event")

    return {"message": "Profile updated successfully"}


@router.post("/event/{eventId}/rsvp")
async def rsvp(
    request: Request, eventId: str, user_id: Optional[int] = Depends(get_current_user)
):
    """
    API endpoint for RSVPing to an event.
    """
    print(f"[rsvp API] Function called with eventId: {eventId}, user_id: {user_id}")
    # Get form data from request - this is async and fast
    form_info = await request.form()
    # Convert form data to dict
    form_data = dict(form_info)
    print(f"[rsvp API] Received form data: {form_data}")

    @database_sync_to_async
    def rsvp_for_event(request, eventId, user_id, form_data):
        user = CustomUser.objects.filter(id=user_id).first() if user_id else None
        form_data_final = None

        try:
            event = Event.objects.get(eventId=eventId)
        except Event.DoesNotExist:
            return {"error": "Event not found"}

        # Delete any existing RSVPs for this user/email
        if user:
            RSVPTicket.objects.filter(event=event, email=user.email).delete()
            Ticket.objects.filter(event=event, guestEmail=user.email).delete()
            event.guest_list.remove(user)

            # Check for existing RSVP
            existing_rsvp = RSVPTicket.objects.filter(
                event=event, email=user.email
            ).first()
            if existing_rsvp:
                return {"message": "You have an RSVP to this event."}

            # Check if display_on_guestlist is in form_data, default to False if not present
            display_on_guestlist = False
            if "display_on_guestlist" in form_data:
                display_on_guestlist = form_data["display_on_guestlist"] == "true"

            form_data_final = {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "display_on_guestlist": display_on_guestlist,
            }
        else:
            # For non-authenticated users
            # Check if required fields are present
            required_fields = ["email", "first_name", "last_name"]
            missing_fields = [
                field for field in required_fields if field not in form_data
            ]

            if missing_fields:
                return {
                    "error": f"Missing required fields: {', '.join(missing_fields)}"
                }

            # Delete any existing RSVPs for this email
            if "email" in form_data:
                RSVPTicket.objects.filter(
                    event=event, email=form_data["email"]
                ).delete()
                Ticket.objects.filter(
                    event=event, guestEmail=form_data["email"]
                ).delete()

            # Check for existing RSVP
            existing_rsvp = RSVPTicket.objects.filter(
                event=event, email=form_data["email"]
            ).first()
            if existing_rsvp:
                return {"message": "You have an RSVP to this event."}

            # Check if display_on_guestlist is in form_data, default to False if not present
            display_on_guestlist = False
            if "display_on_guestlist" in form_data:
                display_on_guestlist = form_data["display_on_guestlist"] == "true"

            form_data_final = {
                "email": form_data["email"],
                "first_name": form_data["first_name"],
                "last_name": form_data["last_name"],
                "display_on_guestlist": display_on_guestlist,
            }

        # Process the RSVP form
        form = RSVPForm(form_data_final, user=user)

        if form.is_valid():
            rsvp_ticket = form.save(commit=False)
            rsvp_ticket.event = event
            rsvp_ticket.user = user
            rsvp_ticket.save()
            generateTicket(
                request,
                event,
                user if user else None,
                rsvp_ticket.first_name,
                rsvp_ticket.last_name,
                rsvp_ticket.email,
                from_api=True,
            )
            if form_data_final["display_on_guestlist"] and user:
                event.guest_list.add(user)
            print(f"Display on guest list: {form_data_final['display_on_guestlist']}")
            return {"message": "RSVP successful!"}
        else:
            return {"errors": form.errors}

    result = await rsvp_for_event(request, eventId, user_id, form_data)
    print(f"[rsvp API] Returning result: {result}")
    return result


@router.get("/user/{user_id}")
async def get_user_details(user_id: UUID, caller_user_id: Optional[int] = Depends(get_current_user)):
    """
    API endpoint to retrieve comprehensive information about a specific user.
    """
    print(f"[get_user_details API] Function called with user_id: {user_id}")

    @database_sync_to_async
    def get_user_data(user_id):
        try:
            # Get user with related profile in a single query
            user = CustomUser.objects.select_related('user_profile').get(user_id=user_id)
            user_profile = user.user_profile

            # Get profile photo URL
            profile_photo_url = (
                user_profile.profile_photo.url
                if user_profile.profile_photo
                else None
            )

            # Get profile QR code URL
            profile_qr_code_url = (
                user_profile.profile_qr_code.url
                if user_profile.profile_qr_code
                else None
            )

            # Get college information
            college_data = None
            if user_profile.college:
                college_data = {
                    "id": user_profile.college.id,
                    "name": user_profile.college.name,
                    "state": user_profile.college.state,
                    "city": user_profile.college.city,
                }

            # Get user's groups
            groups = list(user_profile.group.all().values("id", "name"))

            friend_amount = user_profile.friends.count()

            # Get user's crews
            crew_memberships = []
            for crew_member in CrewMember.objects.filter(user=user).select_related('crew', 'crew__created_by')[:20]:
                crew_memberships.append({
                    "crewId": str(crew_member.crew.crewId),
                    "name": crew_member.crew.name,
                })

            # Get user's favorite events (limit for performance)
            favorite_events = []
            for event in user_profile.favorite_events.all()[:20]:
                favorite_events.append({
                    "eventId": str(event.eventId),
                    "title": event.title,
                    "date": event.date,
                    "header_photo": event.header_photo.url if event.header_photo else None,
                    "event_host": {
                        "username": event.host.username,
                    },
                })

            # Get user's purchased events (limit for performance)
            purchased_events = []
            for event in user_profile.purchased_events.all()[:20]:
                purchased_events.append({
                    "eventId": str(event.eventId),
                    "title": event.title,
                    "date": event.date,
                    "header_photo": event.header_photo.url if event.header_photo else None,
                    "event_host": {
                        "username": event.host.username,
                    },
                })

            # Get user's hosted events (if they are a host)
            hosted_events = []
            for event in Event.objects.filter(host=user)[:20]:
                hosted_events.append({
                    "eventId": str(event.eventId),
                    "title": event.title,
                    "date": event.date,
                    "header_photo": event.header_photo.url if event.header_photo else None,
                })

            return {
                "user": {
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "date_joined": user.date_joined,
                    "email_verified": user.email_verified,
                },
                "profile": {
                    "profile_photo": profile_photo_url,
                    "profile_qr_code": profile_qr_code_url,
                    "college": college_data,
                    "groups": groups,
                    "friend_amount": friend_amount,
                    "crew_memberships": crew_memberships,
                    "favorite_events": favorite_events,
                    "purchased_events": purchased_events,
                    "hosted_events": hosted_events,
                },
            }
        except CustomUser.DoesNotExist:
            print(f"[get_user_details API] User not found with ID: {user_id}")
            return None
        except Exception as e:
            print(f"[get_user_details API] Error retrieving user data: {str(e)}")
            return None

    user_data = await get_user_data(user_id)
    if user_data is None:
        raise HTTPException(status_code=404, detail="User not found")

    print(
        f"[get_user_details API] Returning details for user: {user_data['user']['username']}"
    )

    return {"user_details": user_data}


@router.get("/crew/{crew_id}")
async def get_crew_details(crew_id: UUID, user_id: Optional[int] = Depends(get_current_user)):
    """
    API endpoint to retrieve comprehensive information about a specific crew.
    """
    print(f"[get_crew_details API] Function called with crew_id: {crew_id}")

    @database_sync_to_async
    def get_crew_data(crew_id):
        try:
            # Get crew with related data in optimized queries
            crew = Crew.objects.select_related('created_by', 'created_by__user_profile').get(crewId=crew_id)

            # Get crew creator profile information
            creator_profile = crew.created_by.user_profile if hasattr(crew.created_by, 'user_profile') else None
            creator_data = {
                "user_id": str(crew.created_by.user_id),
                "username": crew.created_by.username,
                "first_name": crew.created_by.first_name,
                "last_name": crew.created_by.last_name,
                "profile_photo": (
                    creator_profile.profile_photo.url
                    if creator_profile and creator_profile.profile_photo
                    else None
                ),
            }

            # Get all crew members with their profiles
            crew_members = []
            for crew_member in CrewMember.objects.filter(crew=crew).select_related('user', 'user__user_profile'):
                member_profile = crew_member.user.user_profile if hasattr(crew_member.user, 'user_profile') else None
                crew_members.append({
                    "user": {
                        "user_id": str(crew_member.user.user_id),
                        "username": crew_member.user.username,
                        "first_name": crew_member.user.first_name,
                        "last_name": crew_member.user.last_name,
                    },
                    "profile": {
                        "profile_photo": (
                            member_profile.profile_photo.url
                            if member_profile and member_profile.profile_photo
                            else None
                        ),
                    },
                    "membership_details": {
                        "joined_at": crew_member.joined_at,
                        "is_admin": crew_member.is_admin,
                    },
                })

            # Get shared events for this crew (limit for performance)
            from eventManagementApp.models import SharedEvent
            shared_events = []
            for shared_event in SharedEvent.objects.filter(crew=crew).select_related('event', 'sender')[:20]:
                shared_events.append({
                    "event": {
                        "eventId": str(shared_event.event.eventId),
                        "title": shared_event.event.title,
                        "date": shared_event.event.date,
                        "header_photo": shared_event.event.header_photo.url if shared_event.event.header_photo else None,
                    },
                    "sender": {
                        "username": shared_event.sender.username,
                        "first_name": shared_event.sender.first_name,
                        "last_name": shared_event.sender.last_name,
                    },
                    "shared_at": shared_event.shared_at,
                })

            return {
                "crewId": str(crew.crewId),
                "name": crew.name,
                "bio": crew.bio,
                "created_at": crew.created_at,
                "created_by": creator_data,
                "members": crew_members,
                "member_count": len(crew_members),
                "shared_events": shared_events,
            }
        except Crew.DoesNotExist:
            print(f"[get_crew_details API] Crew not found with ID: {crew_id}")
            return None
        except Exception as e:
            print(f"[get_crew_details API] Error retrieving crew data: {str(e)}")
            return None

    crew_data = await get_crew_data(crew_id)
    if crew_data is None:
        raise HTTPException(status_code=404, detail="Crew not found")

    print(
        f"[get_crew_details API] Returning details for crew: {crew_data['name']}"
    )

    return {"crew_details": crew_data}


@router.get("/user/test/friends")
async def get_user_friends(user_id: Optional[int] = Depends(get_current_user)):
    """
    API endpoint to retrieve friends of a specific user.
    """
    print(f"[get_user_friends API] Function called with user_id: {user_id}")

    @database_sync_to_async
    def get_user_friends_data(user_id):
        try:
            user = CustomUser.objects.select_related('user_profile').get(id=user_id)
            friends = user.user_profile.friends.all().select_related('user')[:20]
            friends_data = []
            for friend in friends:
                friend_data = {
                    "user_id": str(friend.user.user_id),
                    "username": friend.user.username,
                    "first_name": friend.user.first_name,
                    "last_name": friend.user.last_name,
                    "profile_photo": friend.profile_photo.url if friend.profile_photo else None,
                }
                friends_data.append(friend_data)
            return friends_data
        except CustomUser.DoesNotExist:
            print(f"[get_user_friends API] User not found with ID: {user_id}")
            return None
        except Exception as e:
            print(f"[get_user_friends API] Error retrieving user friends: {str(e)}")
            return None
    
    friends_data = await get_user_friends_data(user_id)
    if friends_data is None:
        raise HTTPException(status_code=404, detail="Friends not found")

    print(f"[get_user_friends API] Returning friends for user: {user_id}")
    return {"friends": friends_data}
