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
    # Universal QR code fields - one QR code per user for all events
    universal_qr_code: Optional[str] = None
    universal_qr_code_image_url: Optional[str] = None
    status: str
    eventDate: date
    eventStartTime: time
    eventEndTime: time
    
    
    class Config:
        from_attributes = True
        populate_by_name = True


class UniversalQRResponse(BaseModel):
    """Pydantic model for universal QR code response"""
    
    user_id: str
    username: str
    universal_qr_code: Optional[str] = None
    universal_qr_code_image_url: Optional[str] = None
    has_qr_code: bool
    qr_generated_at: Optional[str] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True


class QRCodeInfo(BaseModel):
    """Pydantic model for QR code information"""
    
    universal_qr_code: Optional[str] = None
    universal_qr_code_image_url: Optional[str] = None
    has_qr_code: bool
    
    class Config:
        from_attributes = True
        populate_by_name = True


class GuestInfo(BaseModel):
    """Pydantic model for guest ticket information"""
    
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True


class DetailedEventInfo(BaseModel):
    """Pydantic model for detailed event information"""
    
    event_id: str
    title: str
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    header_photo: Optional[str] = None
    description: Optional[str] = None
    venue: Optional[str] = None
    ticketing: Optional[str] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True


class DetailedTicketInfo(BaseModel):
    """Pydantic model for detailed ticket information"""
    
    ticket_id: str
    main_id: str
    status: str
    created_at: str
    stripe_session_id: Optional[str] = None
    event: DetailedEventInfo
    guest_info: Optional[GuestInfo] = None
    qr_code: Optional[QRCodeInfo] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True


class TicketStatistics(BaseModel):
    """Pydantic model for ticket statistics"""
    
    valid: int
    scanned: int
    invalid: int
    
    class Config:
        from_attributes = True
        populate_by_name = True


class UserTicketsResponse(BaseModel):
    """Pydantic model for user tickets response"""
    
    user_id: str
    username: str
    total_tickets: int
    statistics: TicketStatistics
    tickets: List[DetailedTicketInfo]
    has_universal_qr: Optional[bool] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True