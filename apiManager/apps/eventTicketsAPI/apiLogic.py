from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from asgiref.sync import sync_to_async
import uuid
from urllib.parse import urlencode

from django.conf import settings
from django.urls import reverse
from eventTicketsApp.models import Ticket, RSVPTicket
from fastapi import Depends
from apiManager.dependencies import get_current_user


router = APIRouter()


# Pydantic models for request/response validation
class CartItem(BaseModel):
    ticket_id: str
    eventId: str
    ticket_name: str
    ticket_price: float
    quantity: int

class CartRequest(BaseModel):
    cart: List[CartItem]

class CartResponse(BaseModel):
    message: str
    cartSaved: bool

class ErrorResponse(BaseModel):
    error: str
    received_data: Optional[Dict[str, Any]] = None
    missing_fields: Optional[List[str]] = None
    
@router.post("/saveMobileCart", response_model=CartResponse, responses={400: {"model": ErrorResponse}})
async def save_mobile_cart(cart_request: CartRequest, request: Request, user_id: str = Depends(get_current_user)):
    """
    Save cart data from mobile app and return web checkout URL.
    
    This endpoint accepts cart data from the mobile app, validates it,
    stores it in the session with a unique ID, and returns a success response.
    
    Authentication is required to use this endpoint.
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    @sync_to_async
    def process_cart_data(cart_data, request):
        try:
            # Format cart data for session storage
            formatted_cart = {}
            for item in cart_data:
                ticket_id = item.ticket_id
                formatted_cart[ticket_id] = {
                    "eventId": item.eventId,
                    "name": item.ticket_name,
                    "price": str(item.ticket_price),
                    "quantity": item.quantity,
                }

            # Generate a unique cart ID
            cart_id = str(uuid.uuid4())

            # Store cart in session with the unique ID
            request.session[f"mobile_cart_{cart_id}"] = formatted_cart
            print("Stored cart data:", formatted_cart)

            # Build the web checkout URL with cart ID
            web_base_url = settings.SITE_URL
            checkout_path = reverse("eventTicketsAPI:processCheckout")
            params = urlencode({"cart_id": cart_id})
            web_checkout_url = f"{web_base_url}{checkout_path}?{params}"

            return {
                "message": "Cart saved successfully",
                "cartSaved": True,
            }, None
        except Exception as e:
            print(f"Error saving mobile cart: {str(e)}")
            return None, str(e)
    
    try:
        print("Received request data:", cart_request.dict())
        
        # Validate cart data
        if not cart_request.cart:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Cart data must be an array", "received_data": cart_request.dict()}
            )
        
        result, error_message = await process_cart_data(cart_request.cart, request)
        
        if error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": error_message, "received_data": cart_request.dict()}
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in save_mobile_cart: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e), "received_data": cart_request.dict() if hasattr(cart_request, 'dict') else None}
        )

# Endpoint implementation removed as it was replaced by the POST version above
    