from typing import Optional
from channels.db import database_sync_to_async
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
import bleach
import uuid
from datetime import date

# Django imports
from django.utils import timezone
from coreApp.forms import RSVPForm
from eventManagementApp.models import Event, CouponCode
from accountManagementApp.models import UserProfile
from eventTicketsApp.models import RSVPTicket, Ticket
from eventTicketsApp.views import generateTicket
from socialApp.models import Crew, CrewMember

# API Manager imports
from .serializers import ExplorePageEvent, EventDetailsSerializer, RSVPInformation
from apiManager.dependencies import get_current_user
from apiManager.utilities.notify_by_bot import notify_by_bot
from apiManager.utilities.device_info import get_device_info
from authenticationApp.models import CustomUser
from uuid import UUID
from .version_middleware import VersionCheckMiddleware
from opentelemetry.trace import get_tracer
from opentelemetry import trace
import logging


router = APIRouter()

logger = logging.getLogger("wave.api")
tracer = trace.get_tracer(__name__)


@router.get("/ping")
async def ping(
    request: Request,
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        return {"message": "Core API is running!"}
    except Exception as e:
        await notify_by_bot(
            f"**[API: ping]** \n\n Error in ping endpoint: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail=f"Error in ping endpoint: {str(e)}")


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
async def get_events(
    request: Request,
    platform: Optional[str] = None,
    offset: int = 0,
    limit: int = 10,
):
    """
    API endpoint to retrieve events for the explore page with pagination.
    Returns 10 events by default, use offset to get more events.
    """
    print(f"[get_events API] Function called with offset={offset}, limit={limit}")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_events_data(offset, limit):
        # Get total count of all events
        total_events = Event.objects.count()
        
        # Get paginated events
        events_queryset = Event.objects.order_by('date')[offset:offset + limit]
        
        print(f"[DEBUG] Total events in database: {Event.objects.count()}")
        print(f"[DEBUG] Future events: {Event.objects.filter(date__gte=date.today()).count()}")
        print(f"[DEBUG] Past events: {Event.objects.filter(date__lt=date.today()).count()}")
        
        events_list = []
        for event in events_queryset:
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
        
        print(f"[get_events API] Retrieved {len(events_list)} events from database (offset={offset}, limit={limit})")
        return events_list, total_events

    try:
        # Get the data and convert to Pydantic models
        events_data, total_count = await get_events_data(offset, limit)
        events = [ExplorePageEvent(**event_data) for event_data in events_data]

        # Calculate pagination metadata
        has_more = (offset + len(events_data)) < total_count
        next_offset = offset + len(events_data) if has_more else None

        response = {
            "events": events,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total_count": total_count,
                "returned_count": len(events_data),
                "has_more": has_more,
                "next_offset": next_offset
            }
        }
        print(f"[get_events API] Returning {len(events)} events in response with pagination info")
        return response
    except Exception as e:
        await notify_by_bot(
            f"**[API: get_events]** \n\n Error fetching events: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail=f"Error fetching events: {str(e)}")


@router.get("/categories")
async def get_categories(
    request: Request,
    platform: Optional[str] = None,
):
    """
    API endpoint to retrieve all event categories from the EXPLORE_TYPE_CHOICES.
    """
    print("[get_categories API] Function called")

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_categories_data():
        # Return the categories from the Event model's EXPLORE_TYPE_CHOICES
        categories = [
            {"value": value, "label": label}
            for value, label in Event.EXPLORE_TYPE_CHOICES
        ]
        print(f"[get_categories API] Retrieved {len(categories)} categories")
        return categories

    try:
        categories = await get_categories_data()
        response = {"categories": categories}
        print(
            f"[get_categories API] Returning response with {len(categories)} categories"
        )
        return response
    except Exception as e:
        await notify_by_bot(
            f"**[API: get_categories]** \n\n Error fetching categories: error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching categories: {str(e)}"
        )


@router.get("/event/{eventId}")
async def get_event_details(
    eventId: str, request: Request, platform: Optional[str] = None
):
    """
    API endpoint to retrieve details of a specific event.
    """
    print(f"[get_event_details API] Function called with eventId: {eventId}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

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

            # Sanitize HTML in the description to prevent XSS attacks
            sanitized_description = (
                bleach.clean(event.description) if event.description else ""
            )

            return {
                "eventId": str(event.eventId),
                "title": event.title,
                "date": event.date,
                "start_time": event.start_time,
                "end_time": event.end_time,
                "description": sanitized_description,
                "event_type": event.event_type,
                "ticketing": str(event.ticketing),
                "location": {
                    "building_name": event.building_name,
                    "street": event.street,
                    "apt_suite_unit": event.apt_suite_unit,
                    "city": event.city,
                    "state": event.state,
                    "zip_code": event.zip_code,
                    "country": event.country,
                    "hide_address": event.hide_address,
                },
                "header_photo": header_photo_url,
                "body_photo_one": body_photo_one_url,
                "body_photo_two": body_photo_two_url,
                "body_photo_three": body_photo_three_url,
                "body_photo_four": body_photo_four_url,
                "body_photo_five": body_photo_five_url,
                "host": host_data,
                "guest_list": guest_list,
                "is_favorite": is_favorite,
                "rsvp_required": rsvp_required,
                "crew_discount": event.crew_discount,
                "minimum_crew_size": event.minimum_crew_size,
                "crew_discount_percentage": event.crew_discount_percentage,
                "show_guest_list": event.show_guest_list,
                "forAllDisplay": bool(event.forAllDisplay),
                "forCollegesDisplay": bool(event.forCollegesDisplay),
                "coupons_activated": bool(event.couponsActivated),
            }
        except Event.DoesNotExist:
            print(f"[get_event_details API] Event not found with ID: {eventId}")
            return None

    @database_sync_to_async
    def get_event_ticket_data(eventId):
        """
        Retrieve ticket information for paid events.
        """
        try:
            event = Event.objects.get(eventId=eventId)
            
            # Check if event is paid ticketing
            if str(event.ticketing).lower() != 'paid':
                print(f"[get_event_ticket_data API] Event is not paid ticketing, returning empty list")
                return []
                
            # Import PaidFreeTicket model
            from eventTicketsApp.models import PaidFreeTicket
            
            # Get all ticket types for this event
            ticket_types = PaidFreeTicket.objects.filter(event=event)
            
            tickets_data = []
            for ticket_type in ticket_types:
                ticket_info = {
                    "id": str(ticket_type.ticket_id),
                    "ticket_name": ticket_type.ticket_name,
                    "price": float(ticket_type.ticket_price) if ticket_type.ticket_price else 0.0,
                    "description": ticket_type.ticket_description,
                    "available_quantity": ticket_type.ticket_quantity,
                    "sold_quantity": ticket_type.ticket_sold,
                    "available_tickets": ticket_type.available_tickets(),
                    "crew_discounted_price": (
                        float(ticket_type.crew_discounted_price) 
                        if ticket_type.crew_discounted_price 
                        else None
                    ),
                    "stripe_price_id": ticket_type.stripePriceId,
                    "deadline": ticket_type.deadline,
                }
                tickets_data.append(ticket_info)
            
            print(f"[get_event_ticket_data API] Retrieved {len(tickets_data)} ticket types for paid event")
            return tickets_data
            
        except Event.DoesNotExist:
            print(f"[get_event_ticket_data API] Event not found with ID: {eventId}")
            return []
        except Exception as e:
            print(f"[get_event_ticket_data API] Error retrieving tickets: {str(e)}")
            return []

    @database_sync_to_async
    def get_event_coupons_data(eventId):
        """
        Retrieve all coupons for an event.
        """
        try:
            event = Event.objects.get(eventId=eventId)
            
            # Get all coupons for this event using the related_name
            coupons = event.event_coupons.all()
            
            coupons_data = []
            for coupon in coupons:
                coupon_info = {
                    "coupon_id": str(coupon.coupon_id),
                    "code": coupon.code,
                    "discount_percentage": coupon.discount_percentage,
                    "created_at": coupon.created_at.isoformat() if coupon.created_at else None,
                    "updated_at": coupon.updated_at.isoformat() if coupon.updated_at else None,
                }
                coupons_data.append(coupon_info)
            
            print(f"[get_event_coupons_data API] Retrieved {len(coupons_data)} coupons for event")
            return coupons_data
            
        except Event.DoesNotExist:
            print(f"[get_event_coupons_data API] Event not found with ID: {eventId}")
            return []
        except Exception as e:
            print(f"[get_event_coupons_data API] Error retrieving coupons: {str(e)}")
            return []

    event_data = await get_event_data(eventId)
    if event_data is None:
        await notify_by_bot(
            f"**[API: get_event_details]** \n\n Event not found: eventId={eventId} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=404, detail="Event not found")

    # Get ticket information if event is paid
    tickets_data = await get_event_ticket_data(eventId)
    event_data["paid_free_tickets"] = tickets_data

    # Get coupon information for the event
    coupons_data = await get_event_coupons_data(eventId)
    event_data["coupons"] = coupons_data

    print(
        f"[get_event_details API] Returning details for event: {event_data.get('title')}"
    )

    return {"event": event_data}


@router.get("/event/{eventId}/host_profile")
async def get_event_host_profile(
    eventId: str, request: Request, platform: Optional[str] = None
):
    """
    API endpoint to retrieve the host profile for a specific event.
    """
    print(f"[get_event_host_profile API] Function called with eventId: {eventId}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

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
        await notify_by_bot(
            f"**[API: get_event_host_profile]** \n\n Event not found: eventId={eventId} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=404, detail="Event not found")

    print(
        f"[get_event_host_profile API] Returning host profile for: {host_data.get('first_name')} {host_data.get('last_name')}"
    )
    return {"host_profile": host_data}


@router.get("/event/{eventId}/guests")
async def get_event_guests(
    eventId: str, request: Request, platform: Optional[str] = None
):
    """
    API endpoint to retrieve guests for a specific event.
    """
    print(f"[get_event_guests API] Function called with eventId: {eventId}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_guests_data(eventId):
        try:
            event = Event.objects.get(eventId=eventId)

            # Check if event allows showing guest list
            if not event.show_guest_list:
                return []

            guests = event.guest_list.all()
            guests_data = []

            for guest in guests:
                try:
                    user_profile = guest.user_profile
                    guest_info = {
                        "id": str(guest.id),
                        "user_id": str(guest.user_id),
                        "username": guest.username,
                        "profile_photo": (
                            user_profile.profile_photo.url
                            if user_profile.profile_photo
                            else None
                        ),
                    }
                    guests_data.append(guest_info)
                except AttributeError:
                    # Skip guests without user profiles
                    continue

            print(
                f"[get_event_guests API] Retrieved {len(guests_data)} guests for event"
            )
            return guests_data
        except Event.DoesNotExist:
            print(f"[get_event_guests API] Event not found with ID: {eventId}")
            return None

    guests_data = await get_guests_data(eventId)
    if guests_data is None:
        await notify_by_bot(
            f"**[API: get_event_guests]** \n\n Event not found: eventId={eventId} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=404, detail="Event not found")

    return {
        "guests": guests_data,
        "total_guests": len(guests_data),
        "event_id": eventId,
    }


@router.get("/event/{eventId}/guests/preview")
async def get_event_guests_preview(
    eventId: str, request: Request, platform: Optional[str] = None
):
    """
    API endpoint to retrieve 3 guests from the guestlist for preview.
    """
    print(f"[get_event_guests_preview API] Function called with eventId: {eventId}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_guests_preview_data(eventId):
        try:
            event = Event.objects.get(eventId=eventId)

            # Check if event allows showing guest list
            if not event.show_guest_list:
                return []

            # Get first 3 guests from the guest list
            guests = event.guest_list.all()[:3]

            guests_data = []
            for guest in guests:
                try:
                    user_profile = guest.user_profile
                    guest_info = {
                        "id": str(guest.id),
                        "user_id": str(guest.user_id),
                        "username": guest.username,
                        "first_name": guest.first_name,
                        "last_name": guest.last_name,
                        "profile_photo": (
                            user_profile.profile_photo.url
                            if user_profile.profile_photo
                            else None
                        ),
                    }
                    guests_data.append(guest_info)
                except AttributeError:
                    # Skip guests without user profiles
                    continue

            print(
                f"[get_event_guests_preview API] Retrieved {len(guests_data)} guests for preview"
            )
            return guests_data

        except Event.DoesNotExist:
            print(f"[get_event_guests_preview API] Event not found with ID: {eventId}")
            return None

    guests_data = await get_guests_preview_data(eventId)

    if guests_data is None:
        await notify_by_bot(
            f"**[API: get_event_guests_preview]** \n\n Event not found: eventId={eventId} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=404, detail="Event not found")

    return {"guests": guests_data, "total_guests": len(guests_data), "is_preview": True}


@router.get("/event/{eventId}/guests/all")
async def get_event_guests_all(
    eventId: str, request: Request, platform: Optional[str] = None
):
    """
    API endpoint to retrieve all guests from the guestlist for an event.
    """
    print(f"[get_event_guests_all API] Function called with eventId: {eventId}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_all_guests_data(eventId):
        try:
            event = Event.objects.get(eventId=eventId)

            # Check if event allows showing guest list
            if not event.show_guest_list:
                return []

            # Get all guests from the guest list
            guests = event.guest_list.all()

            guests_data = []
            for guest in guests:
                try:
                    user_profile = guest.user_profile
                    guest_info = {
                        "id": str(guest.id),
                        "user_id": str(guest.user_id),
                        "username": guest.username,
                        "first_name": guest.first_name,
                        "last_name": guest.last_name,
                        "profile_photo": (
                            user_profile.profile_photo.url
                            if user_profile.profile_photo
                            else None
                        ),
                    }
                    guests_data.append(guest_info)
                except AttributeError:
                    # Skip guests without user profiles
                    continue

            print(
                f"[get_event_guests_all API] Retrieved {len(guests_data)} total guests"
            )
            return guests_data

        except Event.DoesNotExist:
            print(f"[get_event_guests_all API] Event not found with ID: {eventId}")
            return None

    guests_data = await get_all_guests_data(eventId)

    if guests_data is None:
        await notify_by_bot(
            f"**[API: get_event_guests_all]** \n\n Event not found: eventId={eventId} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=404, detail="Event not found")

    return {
        "guests": guests_data,
        "total_guests": len(guests_data),
        "is_preview": False,
    }


@router.post("/event/{eventId}/toggleFavorite")
async def toggleFavorite(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint toggling a favorite on an event
    """

    with tracer.start_as_current_span("toggleFavorite-handler") as span:
        span.set_attribute("event.id", eventId)
        span.set_attribute("user.id", user_id)
        span.set_attribute("platform", platform or "unknown")

        logger.info(
            "Toggling favorite status for event",
            extra={"eventId": eventId, "user_id": user_id, "platform": platform},
        )

        user_agent_str = request.headers.get("user-agent", "")
        device_data = get_device_info(user_agent_str)
        device_info = device_data["device_info"]

        @database_sync_to_async
        def toggle_fav_event(eventId, user_id):
            with tracer.start_as_current_span("toggleFavorite-db-operation"):
                try:
                    user = CustomUser.objects.get(id=user_id)
                    event = Event.objects.get(eventId=eventId)
                    user_profile = UserProfile.objects.get(user=user)

                    if event in user_profile.favorite_events.all():
                        user_profile.favorite_events.remove(event)
                        logger.info(
                            f"Removed event {event.title} from favorites",
                            extra={"user": user.username, "eventId": eventId},
                        )
                    else:
                        user_profile.favorite_events.add(event)
                        logger.info(
                            f"Added event {event.title} to favorites",
                            extra={"user": user.username, "eventId": eventId},
                        )

                    user_profile.save()
                    return True

                except CustomUser.DoesNotExist:
                    logger.error(
                        "User does not exist",
                        extra={"user_id": user_id},
                    )
                except Event.DoesNotExist:
                    logger.error(
                        "Event does not exist",
                        extra={"eventId": eventId},
                    )
                except UserProfile.DoesNotExist:
                    logger.error(
                        "UserProfile does not exist",
                        extra={"user_id": user_id},
                    )
                except Exception as e:
                    logger.exception("Unexpected error in toggle_fav_event")
                return False

        try:
            success = await toggle_fav_event(eventId, user_id)
            if not success:
                logger.warning(
                    "Failed to favorite/unfavorite event",
                    extra={
                        "eventId": eventId,
                        "user_id": user_id,
                        "platform": platform,
                    },
                )
                await notify_by_bot(
                    f"**[API: toggleFavorite]** \n\n Could not favorite event: eventId={eventId}, user_id={user_id} \n\n Platform: {platform}",
                    platform or "Unknown",
                    "ERROR",
                    device_info,
                )
                raise HTTPException(status_code=404, detail="Could not favorite event")

            logger.info(
                "Successfully toggled favorite status",
                extra={"eventId": eventId, "user_id": user_id},
            )
            return {"message": "Profile updated successfully"}

        except Exception as e:
            logger.exception("Unhandled exception in toggleFavorite")
            await notify_by_bot(
                f"**[API: toggleFavorite]** \n\n Unhandled exception: eventId={eventId}, user_id={user_id}, error={str(e)} \n\n Platform: {platform}",
                platform or "Unknown",
                "ERROR",
                device_info,
            )
            raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/event/{eventId}/isFavorite")
async def check_event_favorite(
    eventId: str,
    request: Request,
    user_id: int = Depends(get_current_user),
    platform: Optional[str] = None,
):
    """
    API endpoint to check if a specific event is in the user's favorites.
    Returns event data if favorited, otherwise returns isFavorite: false.
    """
    print(
        f"[check_event_favorite API] Function called with eventId: {eventId}, user_id: {user_id}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def check_favorite_status(eventId, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            event = Event.objects.get(eventId=eventId)
            user_profile = UserProfile.objects.get(user=user)

            is_favorite = event in user_profile.favorite_events.all()
            print(
                f"[check_event_favorite API] Event {event.title} favorite status for user {user.username}: {is_favorite}"
            )

            if is_favorite:
                return {
                    "isFavorite": True,
                }
            else:
                # Return just the boolean when not favorited
                return {"isFavorite": False}

        except CustomUser.DoesNotExist:
            print(f"[check_event_favorite API] User not found with ID: {user_id}")
            return None
        except Event.DoesNotExist:
            print(f"[check_event_favorite API] Event not found with ID: {eventId}")
            return None
        except UserProfile.DoesNotExist:
            print(
                f"[check_event_favorite API] User profile not found for user ID: {user_id}"
            )
            return None

    favorite_status = await check_favorite_status(eventId, user_id)

    if favorite_status is None:
        await notify_by_bot(
            f"**[API: check_event_favorite]** \n\n User, event, or user profile not found: eventId={eventId}, user_id={user_id} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=404, detail="User, event, or user profile not found"
        )

    return favorite_status


@router.post("/event/{eventId}/rsvp")
async def rsvp(
    request: Request,
    eventId: str,
    user_id: Optional[int] = Depends(get_current_user),
    platform: Optional[str] = None,
):
    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    try:
        form_data = await request.form()

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
                print(
                    f"Display on guest list: {form_data_final['display_on_guestlist']}"
                )
                return {"message": "RSVP successful!"}
            else:
                return {"errors": form.errors}

        result = await rsvp_for_event(request, eventId, user_id, form_data)
        print(f"[rsvp API] Returning result: {result}")
        return result
    except Exception as e:
        await notify_by_bot(
            f"**[API: rsvp]** \n\n Error processing RSVP: eventId={eventId}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=500, detail=f"Error processing RSVP: {str(e)}")


@router.get("/events/search")
async def search_events(
    request: Request,
    q: Optional[str] = None,  # Search query
    category: Optional[str] = None,  # Event category filter
    city: Optional[str] = None,  # City filter
    state: Optional[str] = None,  # State filter
    ticketing: Optional[str] = None,  # Ticketing type filter (free/paid)
    limit: Optional[int] = 20,  # Limit number of results
    platform: Optional[str] = None,
):
    """
    API endpoint to search events with live results.
    Supports filtering by query, category, location, and ticketing type.
    """
    print(
        f"[search_events API] Function called with query: {q}, category: {category}, city: {city}, state: {state}, ticketing: {ticketing}"
    )

    # Get device info
    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def search_events_data(q, category, city, state, ticketing, limit):
        try:
            # Start with all events
            events_queryset = Event.objects.all()

            # Apply search filters
            if q:
                # Search in title and description (case-insensitive)
                events_queryset = events_queryset.filter(
                    title__icontains=q
                ) | events_queryset.filter(description__icontains=q)

            if category:
                events_queryset = events_queryset.filter(event_type=category)

            if city:
                events_queryset = events_queryset.filter(city__icontains=city)

            if state:
                events_queryset = events_queryset.filter(state__icontains=state)

            if ticketing:
                events_queryset = events_queryset.filter(ticketing=ticketing)

            # Apply limit
            if limit and limit > 0:
                events_queryset = events_queryset[:limit]

            # Convert to list format
            events_list = []
            for event in events_queryset:
                header_photo_url = (
                    event.header_photo.url if event.header_photo else None
                )
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
                        "forAllDisplay": bool(
                            event.forAllDisplay
                        ),  # Ensure it's a boolean
                        "forCollegesDisplay": bool(
                            event.forCollegesDisplay
                        ),  # Ensure it's a boolean
                    }
                )

            print(
                f"[search_events API] Found {len(events_list)} events matching search criteria"
            )
            return events_list

        except Exception as e:
            print(f"[search_events API] Error during search: {str(e)}")
            return []

    try:
        # Get the search results
        events_data = await search_events_data(
            q, category, city, state, ticketing, limit
        )
        events = [ExplorePageEvent(**event_data) for event_data in events_data]

        response = {
            "events": events,
            "total_results": len(events),
            "search_params": {
                "query": q,
                "category": category,
                "city": city,
                "state": state,
                "ticketing": ticketing,
                "limit": limit,
            },
        }

        print(f"[search_events API] Returning {len(events)} search results")
        return response
    except Exception as e:
        await notify_by_bot(
            f"**[API: search_events]** \n\n Error searching events: query={q}, error={str(e)} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(
            status_code=500, detail=f"Error searching events: {str(e)}"
        ) from e


@router.get("/event/{eventId}/photos")
async def get_event_body_photos(
    eventId: str, request: Request, platform: Optional[str] = None
):
    """
    API endpoint to retrieve all body photos for a specific event.
    """
    print(f"[get_event_body_photos API] Function called with eventId: {eventId}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def get_event_photos_data(eventId):
        try:
            event = Event.objects.get(eventId=eventId)

            # Collect all body photos that exist
            body_photos = []

            # Check each body photo field and add to list if it exists
            photo_fields = [
                ("body_photo_one", event.body_photo_one),
                ("body_photo_two", event.body_photo_two),
                ("body_photo_three", event.body_photo_three),
                ("body_photo_four", event.body_photo_four),
                ("body_photo_five", event.body_photo_five),
            ]

            for field_name, photo_field in photo_fields:
                if photo_field:
                    body_photos.append(
                        {
                            "field_name": field_name,
                            "photo_url": photo_field.url,
                            "photo_name": (
                                photo_field.name.split("/")[-1]
                                if photo_field.name
                                else None
                            ),
                        }
                    )

            print(
                f"[get_event_body_photos API] Retrieved {len(body_photos)} body photos for event"
            )
            return body_photos

        except Event.DoesNotExist:
            print(f"[get_event_body_photos API] Event not found with ID: {eventId}")
            return None

    photos_data = await get_event_photos_data(eventId)

    if photos_data is None:
        await notify_by_bot(
            f"**[API: get_event_body_photos]** \n\n Event not found: eventId={eventId} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=404, detail="Event not found")

    return {
        "photos": photos_data,
        "total_photos": len(photos_data),
        "event_id": eventId,
    }


@router.get("/event/{eventId}/photos/exists")
async def check_event_body_photos_exist(
    eventId: str, request: Request, platform: Optional[str] = None
):
    """
    API endpoint to check if body photos exist for a specific event.
    Returns true if any body photos exist, false otherwise.
    """
    print(
        f"[check_event_body_photos_exist API] Function called with eventId: {eventId}"
    )

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def check_photos_exist(eventId):
        try:
            event = Event.objects.get(eventId=eventId)

            # Check if any body photo fields have content
            photo_fields = [
                event.body_photo_one,
                event.body_photo_two,
                event.body_photo_three,
                event.body_photo_four,
                event.body_photo_five,
            ]

            photos_exist = any(photo_field for photo_field in photo_fields)

            print(f"[check_event_body_photos_exist API] Photos exist: {photos_exist}")
            return photos_exist

        except Event.DoesNotExist:
            print(
                f"[check_event_body_photos_exist API] Event not found with ID: {eventId}"
            )
            return None

    photos_exist = await check_photos_exist(eventId)

    if photos_exist is None:
        await notify_by_bot(
            f"**[API: check_event_body_photos_exist]** \n\n Event not found: eventId={eventId} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=404, detail="Event not found")

    return {"photos_exist": photos_exist, "event_id": eventId}


@router.get("/event/{eventId}/guests/exists")
async def check_event_guestlist_exists(
    eventId: str, request: Request, platform: Optional[str] = None
):
    """
    API endpoint to check if a guestlist exists for a specific event.
    Returns true if guestlist exists and is public, false otherwise.
    """
    print(f"[check_event_guestlist_exists API] Function called with eventId: {eventId}")

    user_agent_str = request.headers.get("user-agent", "")
    device_data = get_device_info(user_agent_str)
    device_info = device_data["device_info"]

    @database_sync_to_async
    def check_guestlist_exists(eventId):
        try:
            event = Event.objects.get(eventId=eventId)

            # Check if event allows showing guest list and has guests
            guestlist_exists = event.show_guest_list and event.guest_list.exists()

            print(
                f"[check_event_guestlist_exists API] Guestlist exists: {guestlist_exists}"
            )
            return guestlist_exists

        except Event.DoesNotExist:
            print(
                f"[check_event_guestlist_exists API] Event not found with ID: {eventId}"
            )
            return None

    guestlist_exists = await check_guestlist_exists(eventId)

    if guestlist_exists is None:
        await notify_by_bot(
            f"**[API: check_event_guestlist_exists]** \n\n Event not found: eventId={eventId} \n\n Platform: {platform}",
            platform or "Unknown",
            "ERROR",
            device_info,
        )
        raise HTTPException(status_code=404, detail="Event not found")

    return {"guestlist_exists": guestlist_exists, "event_id": eventId}
