from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import date, datetime, time

class CollegeExplorePage(BaseModel):
    """
    Pydantic model for the college data displayed on the explore page.
    """
    collegeId: str  
    name: str
    campus_image: Optional[HttpUrl] = None
    state: str
    city: str
    logo: Optional[HttpUrl] = None
    
    
    class Config:
        from_attributes = True