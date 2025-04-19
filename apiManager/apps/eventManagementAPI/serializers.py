from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime, date, time

class HostEventExplore(BaseModel):
    eventId: str
    title: str
    date: date
    header_photo: Optional[HttpUrl] = None
    state: str
    city: str
    ticketing: str
    
    class Config:
        from_attributes = True


class LocationSerializer(BaseModel):
    building_name: Optional[str] = None
    street: Optional[str] = None
    apt_suite_unit: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    hide_address: bool = False


class HostSerializer(BaseModel):
    id: str
    name: str


class EditEventResponseSerializer(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    date: datetime
    location: LocationSerializer
    host: HostSerializer
    isInCollege: bool
    rsvpList: List[Dict[str, Any]] = []
    paidFreeTickets: List[Dict[str, Any]] = []
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EditEventSerializer(BaseModel):
    message: str
    event: EditEventResponseSerializer
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        
        
        
class EventDetailSerializer(BaseModel):
    eventId: str
    status: str
    title: str
    event_type: str
    date: date
    start_time: time
    end_time: time
    description: Optional[str] = None
    ticketing: Optional[str] = None
    location: LocationSerializer
    header_photo: Optional[HttpUrl] = None
    body_photo_one: Optional[HttpUrl] = None
    body_photo_two: Optional[HttpUrl] = None
    body_photo_three: Optional[HttpUrl] = None
    body_photo_four: Optional[HttpUrl] = None
    body_photo_five: Optional[HttpUrl] = None
    crew_discount: Optional[bool] = None
    minimum_crew_size: Optional[int] = None
    crew_discount_percentage: Optional[float] = None
    couponsActivated: Optional[bool] = None
    show_guest_list: Optional[bool] = None
    forAllDisplay: Optional[bool] = None
    forCollegesDisplay: Optional[bool] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }