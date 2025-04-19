from typing import Optional
from asgiref.sync import sync_to_async
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
# Django imports
from coreApp.forms import RSVPForm
from eventManagementApp.models import Event
from accountManagementApp.models import UserProfile
from eventTicketsApp.models import RSVPTicket, Ticket
from eventTicketsApp.views import generateTicket
# API Manager imports
from .serializers import ExplorePageEvent, EventDetailsSerializer, RSVPInformation
from apiManager.dependencies import get_current_user
from authenticationApp.models import CustomUser
from uuid import UUID



router = APIRouter()

@router.get("/ping")
async def ping():
    return {"message": "Core API is running!"}


@router.get("/events")
async def get_events():
    """
    API endpoint to retrieve events for the explore page.
    """
    print("[get_events API] Function called")
    @sync_to_async
    def get_events_data():
        events_list = []
        for event in Event.objects.all():
            header_photo_url = event.header_photo.url if event.header_photo else None
            events_list.append({
                "eventId": str(event.eventId),  # Convert UUID to string
                "title": event.title,
                "date": event.date,
                "header_photo": header_photo_url,
                "event_type": event.event_type,
                "state": event.state,
                "city": event.city,
                "ticketing": str(event.ticketing),  # Ensure it's a string
                "forAllDisplay": bool(event.forAllDisplay),  # Ensure it's a boolean
                "forCollegesDisplay": bool(event.forCollegesDisplay),  # Ensure it's a boolean
            })
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
    @sync_to_async
    def get_categories_data():
        # Return the categories from the Event model's EXPLORE_TYPE_CHOICES
        categories = [{"value": value, "label": label} for value, label in Event.EXPLORE_TYPE_CHOICES]
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
    @sync_to_async
    def get_event_data(eventId):
        try:
            event = Event.objects.get(eventId=eventId)
            header_photo_url = event.header_photo.url if event.header_photo else None
            return {
                "eventId": str(event.eventId), 
                "title": event.title,
                "description": event.description,
                "date": event.date,
                "header_photo": header_photo_url,
                "country": event.country,
                "street": event.street,
                "apt_suite_unit": event.apt_suite_unit,
                "city": event.city,
                "state": event.state,
                "zip_code": event.zip_code,
                "hide_address": bool(event.hide_address), 
                "ticketing": str(event.ticketing), 
                "start_time": str(event.start_time),  
                "end_time": str(event.end_time),
            }
        except Event.DoesNotExist:
            print(f"[get_event_details API] Event not found with ID: {eventId}")
            return None
    
    event_data = await get_event_data(eventId)
    if event_data is None:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event = EventDetailsSerializer(**event_data)
    print(f"[get_event_details API] Returning details for event: {event_data.get('title')}")
    
    return{"event": event}

@router.get("/event/{eventId}/host_profile")
async def get_event_host_profile(eventId: str):
    """
    API endpoint to retrieve the host profile for a specific event.
    """
    print(f"[get_event_host_profile API] Function called with eventId: {eventId}")
    @sync_to_async
    def get_host_profile(eventId):
        try:
            event = Event.objects.get(eventId=eventId)
            host_profile = event.host.user_profile  # Assuming this is a ForeignKey to UserProfile
            return {
                "profile_photo": host_profile.profile_photo.url if host_profile.profile_photo else None,
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
    
    print(f"[get_event_host_profile API] Returning host profile for: {host_data.get('first_name')} {host_data.get('last_name')}")
    return {"host_profile": host_data}

@router.get("/event/{eventId}/guests")
async def get_event_guests(eventId: str):
    """
    API endpoint to retrieve guests for a specific event.
    """
    print(f"[get_event_guests API] Function called with eventId: {eventId}")
    @sync_to_async
    def get_guests_data(eventId):
        try:
            event = Event.objects.get(eventId=eventId)
            guests = event.guest_list.all()  # Assuming guests is a related name for the ManyToMany field
            guest_photos = [guest.user_profile.profile_photo for guest in guests]  # Adjust according to your User model
            print(f"[get_event_guests API] Retrieved {len(guest_photos)} guests for event")
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
    print(f"[toggleFavorite API] Function called with eventId: {eventId}, user_id: {user_id}")
    @sync_to_async
    def toggle_fav_event(eventId, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            event = Event.objects.get(eventId=eventId)
            user_profile = UserProfile.objects.get(user=user)
            if event in user_profile.favorite_events.all():
                user_profile.favorite_events.remove(event)
                print(f"[toggleFavorite API] Removed event {event.title} from favorites for user {user.username}")
            else:
                user_profile.favorite_events.add(event)
                print(f"[toggleFavorite API] Added event {event.title} to favorites for user {user.username}")
            user_profile.save()
            return True
        except CustomUser.DoesNotExist or Event.DoesNotExist or UserProfile.DoesNotExist:
            print(f"[toggleFavorite API] Error: Could not find user, event, or user profile")
            return False
    success = await toggle_fav_event(eventId, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Could not favorite event")
    
    return {"message": "Profile updated successfully"}

@router.post("/event/{eventId}/rsvp")
async def rsvp(request: Request, eventId: str, user_id: Optional[int] = Depends(get_current_user)):
    """
    API endpoint for RSVPing to an event.
    """
    print(f"[rsvp API] Function called with eventId: {eventId}, user_id: {user_id}")
     # Get form data from request - this is async and fast
    form_info = await request.form()
    # Convert form data to dict
    form_data = dict(form_info)
    print(f"[rsvp API] Received form data: {form_data}")
    @sync_to_async
    def rsvp_for_event(request, eventId, user_id, form_data):
        user = CustomUser.objects.filter(id=user_id).first() if user_id else None
        form_data_final = None

        try:
            event = Event.objects.get(eventId=eventId)
        except Event.DoesNotExist:
            return {"error": "Event not found"}
        
        # if user:
        #     RSVPTicket.objects.filter(event=event, email=user.email).delete()
        #     Ticket.objects.filter(event=event, guestEmail=user.email).delete()
        #     event.guest_list.remove(user)
        # else:
        #     RSVPTicket.objects.filter(event=event, email=form_data['email']).delete()
        #     Ticket.objects.filter(event=event, guestEmail=form_data['email']).delete()                if user:
            existing_rsvp = RSVPTicket.objects.filter(event=event, email=user.email).first()
            if existing_rsvp:
                return {"message": "You have an RSVP to this event."}

            # Check if display_on_guestlist is in form_data, default to False if not present
            display_on_guestlist = False
            if 'display_on_guestlist' in form_data:
                display_on_guestlist = form_data['display_on_guestlist'] == 'true'

                form_data_final = {
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "display_on_guestlist": display_on_guestlist,
                }
            else:
                # Check if required fields are present for non-authenticated users
                required_fields = ['email', 'first_name', 'last_name']
                missing_fields = [field for field in required_fields if field not in form_data]
            
            if missing_fields:
                return {"error": f"Missing required fields: {', '.join(missing_fields)}"}
                
            existing_rsvp = RSVPTicket.objects.filter(event=event, email=form_data['email']).first()
            if existing_rsvp:
                return {"message": "You have an RSVP to this event."}

            # Check if display_on_guestlist is in form_data, default to False if not present
            display_on_guestlist = False
            if 'display_on_guestlist' in form_data:
                display_on_guestlist = form_data['display_on_guestlist'] == 'true'

            form_data_final = {
                "email": form_data['email'],
                "first_name": form_data['first_name'],
                "last_name": form_data['last_name'],
                "display_on_guestlist": display_on_guestlist,
            }
            
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
                from_api=True
            )
            if form_data_final['display_on_guestlist']:
                event.guest_list.add(user)
            print(form_data_final['display_on_guestlist'])
            return {"message": "RSVP successful!"}
        else:
            return {"errors": form.errors}

    result = await rsvp_for_event(request, eventId, user_id, form_data)
    print(f"[rsvp API] Returning result: {result}")
    return result
