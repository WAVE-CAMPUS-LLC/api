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
        
        
        
class CollegeDetails(BaseModel):
    """
    Pydantic model for the detailed information of a college.
    """
    collegeId: str  
    name: str
    address: Optional[str] = None
    city: str
    state: str
    zip_code: Optional[str] = None
    campus_image: Optional[str] = None
    motto: Optional[str] = None
    contact_website: Optional[str] = None
    email_domain: Optional[str] = None
    logo: Optional[str] = None
    
    
    class Config:
        from_attributes = True
        
        
class VerificationRequest(BaseModel):
    code: str
    
    class Config:
        schema_extra = {
            "example": {
                "code": "ABC123"
            }
        }