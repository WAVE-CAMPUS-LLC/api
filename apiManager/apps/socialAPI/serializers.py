from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import date, datetime, time


class MyPassSerializer(BaseModel):
    user_id: str
    id: str
    username: str
    profile_photo: Optional[str] = None
    qr_code: Optional[str] = None


class UserSearchResult(BaseModel):
    user_id: str
    username: str
    first_name: str
    last_name: str
    profile_photo: Optional[str] = None


class CrewSearchResult(BaseModel):
    crew_id: str
    name: str


class SearchResult(BaseModel):
    users: List[UserSearchResult]
    crews: List[CrewSearchResult]
