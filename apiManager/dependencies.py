from fastapi import Header, HTTPException, Depends
from jose import JWTError, jwt
import secrets
import os
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

def get_current_user(authorization: Optional[str] = Header(default=None)):
    if authorization is None:
        return None  # User is not logged in

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = authorization.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token missing subject")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
