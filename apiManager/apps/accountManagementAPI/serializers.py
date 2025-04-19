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
        

class TicketSerializer(BaseModel):
    ticketId: str
    guestFirstName: str
    guestLastName: str
    guestEmail: str
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