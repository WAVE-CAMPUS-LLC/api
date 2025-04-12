from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from authenticationApp.models import CustomUser


router = APIRouter()


@router.get("/ping")
async def ping():
    return {"message": "Authentication API is running!"}