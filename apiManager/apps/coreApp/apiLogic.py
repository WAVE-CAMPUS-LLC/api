from asgiref.sync import sync_to_async
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
# Django imports
from eventManagementApp.models import Event
# API Manager imports
from .serializers import ExplorePageEvent, EventDetailsSerializer


router = APIRouter()

@router.get("/ping")
async def ping():
    return {"message": "Core API is running!"}


@router.get("/events/")
async def get_events():
    """
    API endpoint to retrieve events for the explore page.
    """
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
                "state": event.state,
                "city": event.city,
                "ticketing": str(event.ticketing),  # Ensure it's a string
                "forAllDisplay": bool(event.forAllDisplay),  # Ensure it's a boolean
                "forCollegesDisplay": bool(event.forCollegesDisplay),  # Ensure it's a boolean
            })
        return events_list
    
    # Get the data and convert to Pydantic models
    events_data = await get_events_data()
    events = [ExplorePageEvent(**event_data) for event_data in events_data]
    
    return {"events": events}


@router.get("/event/{eventId}/")
async def get_event_details(eventId: str):
    """
    API endpoint to retrieve details of a specific event.
    """
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
            return None
    
    event_data = await get_event_data(eventId)
    if not event_data:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event = EventDetailsSerializer(**event_data)
    
    return{"event": event}
