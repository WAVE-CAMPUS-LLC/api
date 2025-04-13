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