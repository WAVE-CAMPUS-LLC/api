from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import date, datetime, time


class ProfileOverview(BaseModel):
    id: str
    first_name: str
    last_name: str
    username: str
    email: str
    
    class Config:
        from_attributes = True
        populate_by_name = True


class EventSerializer(BaseModel):
    eventId: str
    title: str
    date: date
    start_time: time
    end_time: time
    header_photo: Optional[str] = None
    description: Optional[str] = None
    location: Dict[str, str] = {
        "address": str,
        "city": str,
        "state": str,
        "zip_code": str,
        "country": str
    }
    
    class Config:
        from_attributes = True
        populate_by_name = True
        

class TicketSerializer(BaseModel):
    ticketId: str
    guestFirstName: str
    guestLastName: str
    guestEmail: str
    event: Optional[EventSerializer] = None
    eventId: str
    eventTitle: str
    qrCodeImage: Optional[str] = None
    status: str
    eventDate: date
    eventStartTime: time
    eventEndTime: time
    
    
    class Config:
        from_attributes = True
        populate_by_name = True