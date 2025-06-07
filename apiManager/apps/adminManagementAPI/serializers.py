from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class EventWithTickets(BaseModel):
    """Event information for events user has tickets to"""

    eventId: str
    title: str
    date: datetime
    header_photo: Optional[str] = None
    event_type: str
    city: str
    state: str
    ticket_type: str  # "rsvp" or "paid"
    ticket_status: Optional[str] = None

    class Config:
        from_attributes = True


class FriendInfo(BaseModel):
    """Friend information"""

    id: int
    username: str
    first_name: str
    last_name: str
    profile_photo: Optional[str] = None

    class Config:
        from_attributes = True


class UserProfileInfo(BaseModel):
    """User profile information"""

    college: Optional[str] = None
    is_campus_manager: bool
    profile_photo: Optional[str] = None
    was_host: bool

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    is_staff: bool
    is_suspended: bool
    groups: List[str]
    date_joined: datetime
    profile_photo: Optional[str] = None
    events_with_tickets: Optional[List[EventWithTickets]] = []
    friends: Optional[List[FriendInfo]] = []
    user_profile: Optional[UserProfileInfo] = None

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    is_staff: Optional[bool] = None
