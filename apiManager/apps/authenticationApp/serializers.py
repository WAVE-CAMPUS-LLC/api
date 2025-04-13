from fastapi import APIRouter
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any

class LoginRequest(BaseModel):
    identifier: str
    password: str
    
    
class JoinRequest(BaseModel):
    data: Dict[str, Any]