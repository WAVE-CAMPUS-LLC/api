from fastapi import Header, HTTPException, Depends
from jose import JWTError, jwt
import secrets
import os
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = authorization.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token missing subject")
        return user_id  # Optionally return the full payload or a user object
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
