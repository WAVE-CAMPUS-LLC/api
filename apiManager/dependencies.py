from fastapi import Header, HTTPException, Depends
from jose import JWTError, jwt, ExpiredSignatureError
import secrets
import os
import traceback
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"


def get_current_user(authorization: Optional[str] = Header(default=None)):
    """Validate the authorization token and return the user ID.

    Args:
        authorization: The Authorization header containing the Bearer token

    Returns:
        The user ID extracted from the token

    Raises:
        HTTPException: If the token is invalid, expired, or missing
    """
    if SECRET_KEY is None:
        print("[Authentication] SECRET_KEY is not configured")
        raise HTTPException(status_code=500, detail="Server configuration error")

    if authorization is None:
        print("[Authentication] No authorization header provided")
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        print(
            "[Authentication] Invalid token format: Authorization header does not start with 'Bearer '"
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1]
    print(f"[Authentication] Processing token: {token[:10]}...")

    try:
        # Decode the token and extract the payload
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Extract user_id from the subject claim
        user_id = payload.get("sub")
        if user_id is None:
            print("[Authentication] Token missing subject claim")
            raise HTTPException(
                status_code=401,
                detail="Token missing subject claim",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check token type
        token_type = payload.get("type")
        if token_type != "access":
            print(f"[Authentication] Invalid token type: {token_type}")
            raise HTTPException(
                status_code=401,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check token expiration explicitly
        exp = payload.get("exp")
        if exp is None:
            print("[Authentication] Token missing expiration claim")
            raise HTTPException(
                status_code=401,
                detail="Token missing expiration",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Log successful authentication
        print(f"[Authentication] Successfully authenticated user_id: {user_id}")
        return int(user_id)  # Ensure we return an int

    except ExpiredSignatureError:
        print("[Authentication] Token has expired")
        raise HTTPException(
            status_code=401,
            detail="Your session has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer", "authError": "true"},
        )
    except JWTError as e:
        error_trace = traceback.format_exc()
        print(f"[Authentication] JWT validation error: {str(e)}\n{error_trace}")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        error_trace = traceback.format_exc()
        print(
            f"[Authentication] Unexpected error during authentication: {str(e)}\n{error_trace}"
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_optional(authorization: Optional[str] = Header(default=None)):
    """Optional authentication - returns user ID if token is valid, None if no token or invalid token.

    Args:
        authorization: The Authorization header containing the Bearer token

    Returns:
        The user ID extracted from the token, or None if not authenticated

    Does not raise HTTPException for missing/invalid tokens
    """
    if SECRET_KEY is None:
        print("[Authentication] SECRET_KEY is not configured")
        return None

    if authorization is None:
        print("[Authentication] No authorization header provided")
        return None

    if not authorization.startswith("Bearer "):
        print(
            "[Authentication] Invalid token format: Authorization header does not start with 'Bearer '"
        )
        return None

    token = authorization.split(" ")[1]
    print(f"[Authentication] Processing optional token: {token[:10]}...")

    try:
        # Decode the token and extract the payload
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Extract user_id from the subject claim
        user_id = payload.get("sub")
        if user_id is None:
            print("[Authentication] Token missing subject claim")
            return None

        # Check token type
        token_type = payload.get("type")
        if token_type != "access":
            print(f"[Authentication] Invalid token type: {token_type}")
            return None

        # Check token expiration explicitly
        exp = payload.get("exp")
        if exp is None:
            print("[Authentication] Token missing expiration claim")
            return None

        # Log successful authentication
        print(f"[Authentication] Successfully authenticated user_id: {user_id}")
        return user_id

    except ExpiredSignatureError:
        print("[Authentication] Token has expired")
        return None
    except JWTError as e:
        print(f"[Authentication] JWT validation error: {str(e)}")
        return None
    except Exception as e:
        print(f"[Authentication] Unexpected error during authentication: {str(e)}")
        return None
