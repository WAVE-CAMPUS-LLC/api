from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import date, datetime, time
from uuid import UUID


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


class UserFriend(BaseModel):
    user_id: str
    username: str
    first_name: str
    last_name: str
    profile_photo: Optional[str] = None


class UserFriends(BaseModel):
    user_friends: List[UserFriend]


class UserCrew(BaseModel):
    crewId: str
    name: str
    bio: Optional[str] = None
    created_at: datetime
    member_photos: List[Optional[str]] = Field(
        default_factory=list, description="List of up to 3 member profile photo URLs"
    )
    is_admin: bool


class UserCrewsResponse(BaseModel):
    user_crews: List[UserCrew]


class CrewMemberDetail(BaseModel):
    user: Dict[str, Any]
    profile: Dict[str, Any]
    membership_details: Dict[str, Any]


class CrewDetailsWithMembers(BaseModel):
    crewId: str
    name: str
    bio: Optional[str] = None
    created_at: datetime
    created_by: Dict[str, Any]
    members: List[CrewMemberDetail]
    member_count: int
    shared_events: List[Dict[str, Any]]
    user_is_member: bool
    user_is_admin: bool


class CrewDetailsWithMembersResponse(BaseModel):
    crew_details: CrewDetailsWithMembers


class CrewPaginationInfo(BaseModel):
    current_page: int
    page_size: int
    total_crews: int
    total_pages: int
    has_next: bool
    has_previous: bool


class UserCrewWithPagination(BaseModel):
    crewId: str
    name: str
    member_count: int


class UserCrewsPaginatedResponse(BaseModel):
    crews: List[UserCrewWithPagination]
    pagination: CrewPaginationInfo


class SurfPostCreate(BaseModel):
    event_id: UUID
    content: str


class SurfPostResponse(BaseModel):
    post_id: UUID
    event_id: UUID
    content: str
    created_at: datetime
    tideup: int
    tidedown: int
    score: int

    class Config:
        orm_mode = True


class VoteRequest(BaseModel):
    post_id: UUID
    vote: int


class SendMessageRequest(BaseModel):
    receiver_username: str
    fixed_message_id: UUID
    event_id: Optional[UUID] = None


class FixedMessageResponse(BaseModel):
    id: UUID
    text: str


class MessageReactionRequest(BaseModel):
    message_id: UUID
    emoji: str


class EventMessageResponse(BaseModel):
    id: UUID
    sender: str
    receiver: str
    fixed_message: str
    event_id: Optional[UUID]
    event_name: Optional[str]
    created_at: datetime
    seen: bool
    seen_at: Optional[datetime]
    reactions: List[dict]
