from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


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

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    is_staff: Optional[bool] = None
