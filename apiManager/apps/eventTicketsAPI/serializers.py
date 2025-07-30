from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, time, date


# These are Pydantic models for FastAPI that will be used to convert
# Django REST Framework serializer data to JSON-compatible formats


class EventModel(BaseModel):
    """Pydantic model for Event data"""

    eventId: str
    title: str
    event_date: Optional[date] = None
    header_photo: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None

    class Config:
        orm_mode = True
        from_attributes = True


class TicketModel(BaseModel):
    """Pydantic model for Ticket data"""

    mainId: Optional[str] = None
    ticketId: Optional[str] = None
    guestFirstName: Optional[str] = None
    guestLastName: Optional[str] = None
    guestEmail: Optional[str] = None
    # Individual ticket QR code fields (restored from legacy system)
    qrCodeData: Optional[str] = None
    qrCodeImage: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    event: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True
        from_attributes = True


class RSVPTicketModel(BaseModel):
    """Pydantic model for RSVPTicket data"""

    ticket_id: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_on_guestlist: Optional[bool] = None
    created_at: Optional[datetime] = None
    event: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True
        from_attributes = True


class CouponModel(BaseModel):
    """Pydantic model for Coupon data"""

    coupon_id: Optional[str] = None
    code: Optional[str] = None
    discount_percentage: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    event: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True
        from_attributes = True
