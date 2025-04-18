from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import date, datetime, time

class RSVPInformation(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    display_on_guestlist: str | None = None


class ExplorePageEvent(BaseModel):
    """
    Pydantic model for the event data displayed on the explore page.
    """
    eventId: str  # Changed from int to str to support UUID
    title: str
    date: date
    header_photo: Optional[HttpUrl] = None
    event_type: str
    state: str
    city: str
    ticketing: str  # Changed from bool to str to match actual data
    forAllDisplay: bool
    forCollegesDisplay: bool
    
    class Config:
        from_attributes = True
        

class EventDetailsSerializer(BaseModel):
    """
    Pydantic model for detailed event view.
    """
    eventId: str  # Changed from int to str to support UUID
    title: str
    description: str
    date: date
    header_photo: Optional[HttpUrl] = None
    country: str
    street: str
    apt_suite_unit: Optional[str] = None
    city: str
    state: str
    zip_code: Optional[str] = None
    hide_address: bool
    ticketing: str  # Changed from bool to str to match actual data
    start_time: Optional[time] = None  # Changed from datetime to time
    end_time: Optional[time] = None  # Changed from datetime to time
    
    class Config:
        from_attributes = True