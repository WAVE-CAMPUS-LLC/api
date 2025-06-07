from datetime import datetime
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    Header,
    UploadFile,
    Form,
    Body,
)
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, Dict, Any
from asgiref.sync import sync_to_async
import traceback
import os
from django.core.files.base import ContentFile
from django.conf import settings

from authenticationApp.models import CustomUser
from authenticationApp.serializers import CustomUserSerializer
from django.contrib.auth import authenticate
from stripeManagementApp.customerSetup import CustomerAccount, ConnectAccount
from rest_framework_simplejwt.tokens import RefreshToken
from adminDashboardApp.models import LoginHistoryModel
from eventManagementApp.models import Event
from eventTicketsApp.models import Ticket
from accountManagementApp.models import UserProfile
from accountManagementApp.serializers import UserProfileSerializer
from accountManagementApp.forms import (
    UpdateProfilePhotoForm,
    UpdatePersonalInfo,
    UpdateContactInfo,
)
from fastapi import Depends
from apiManager.dependencies import get_current_user
from django.shortcuts import get_object_or_404

stripeKey = settings.STRIPE_PUBLISHABLE_KEY


from .serializers import TicketSerializer

router = APIRouter()


@router.get("/profileOverview")
async def profileOverview(user_id: int = Depends(get_current_user)):
    """
    API endpoint for getting profile overview.
    Returns user profile data.
    """
    print(f"[profileOverview] API called with user_id: {user_id}")
    # Log authentication status
    if user_id is None:
        print("[profileOverview] Authentication failed: No user_id provided")
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    @sync_to_async
    def get_profile_overview(user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            user_data = {
                "id": user_id,
                "user_id": str(user.user_id),
                "profile_photo": (
                    user.user_profile.profile_photo.url
                    if user.user_profile.profile_photo
                    else None
                ),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
            }
            print(
                f"[profileOverview] Successfully retrieved profile data for user_id: {user_id}"
            )
            return user_data
        except CustomUser.DoesNotExist:
            print(f"[profileOverview] Error: User with id {user_id} does not exist")
            return None
        except Exception as e:
            error_trace = traceback.format_exc()
            print(
                f"[profileOverview] Unexpected error retrieving profile for user_id {user_id}: {str(e)}\n{error_trace}"
            )
            return None

    try:
        profile_data = await get_profile_overview(user_id)
        if profile_data is None:
            raise HTTPException(status_code=404, detail="User not found")
        return profile_data
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print(f"[profileOverview] Unhandled exception: {str(e)}\n{error_trace}")
            raise HTTPException(status_code=500, detail="Internal server error")
        raise e


@router.get("/profile/detailed")
async def profile_detailed(user_id: int = Depends(get_current_user)):
    """
    API endpoint for getting detailed profile information.
    Returns user profile data including email and phone number.
    """
    print(f"[profile_detailed] API called with user_id: {user_id}")

    @sync_to_async
    def get_profile_detailed(user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            account_type = None
            if user.is_staff:
                account_type = "Staff"
            elif user.is_superuser:
                account_type = "Super User"
            elif user.is_superadmin:
                account_type = "Super Admin"
            else:
                account_type = "User"

            user_data = {
                "id": user_id,
                "user_id": str(user.user_id),
                "profile_photo": (
                    user.user_profile.profile_photo.url
                    if user.user_profile.profile_photo
                    else None
                ),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
                "email": user.email,
                "date_joined": user.date_joined,
                "account_status": user.is_suspended,
                "account_type": account_type,
                "college": (
                    user.user_profile.college.name
                    if user.user_profile.college
                    else None
                ),
            }
            return user_data
        except CustomUser.DoesNotExist:
            return None

    profile_data = await get_profile_detailed(user_id)
    if profile_data is None:
        print(f"[profile_detailed] Error: User not found for user_id: {user_id}")
        raise HTTPException(status_code=404, detail="Event not found")
    print(f"[profile_detailed] Returning profile data: {profile_data}")
    return profile_data


@router.post("/profile/detailed")
async def update_profile_detailed(
    request: Request,
    user_id: int = Depends(get_current_user),
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    profile_photo: Optional[UploadFile] = None,
):
    """
    API endpoint for updating detailed profile information.
    Updates user profile data including email, phone number, and profile photo.
    """
    print(f"[update_profile_detailed] API called with user_id: {user_id}")
    print(
        f"[update_profile_detailed] Request parameters: first_name={first_name}, last_name={last_name}, email={email}"
    )
    print(
        f"[update_profile_detailed] Profile photo provided: {profile_photo is not None}"
    )

    @sync_to_async
    def update_profile_detailed(user_id, first_name, last_name, email, profile_photo):
        try:
            print(
                f"[update_profile_detailed] Updating user data for user_id: {user_id}"
            )
            user = CustomUser.objects.get(id=user_id)
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            if email:
                user.email = email
            user.save()
            print(f"[update_profile_detailed] User data saved successfully")

            # Handle profile photo upload if provided
            if profile_photo:
                # Get or create user profile
                user_profile = user.user_profile
                # Save the uploaded file to the profile_photo field
                if user_profile.profile_photo:
                    # Delete old photo if it exists to avoid storage buildup
                    try:
                        user_profile.profile_photo.delete(save=False)
                    except Exception as e:
                        print(
                            f"[update_profile_detailed] Warning: Could not delete old profile photo: {str(e)}"
                        )

                from django.core.files import File
                from tempfile import NamedTemporaryFile

                # Save the uploaded file to a temporary file
                temp_file = NamedTemporaryFile(delete=False)
                try:
                    temp_file.write(profile_photo.file.read())
                    temp_file.close()

                    # Save the file to the profile_photo field
                    with open(temp_file.name, "rb") as f:
                        filename = profile_photo.filename
                        user_profile.profile_photo.save(filename, File(f), save=True)
                finally:
                    # Clean up the temporary file
                    os.unlink(temp_file.name)

            return True
        except CustomUser.DoesNotExist:
            return False

    success = await update_profile_detailed(
        user_id, first_name, last_name, email, profile_photo
    )
    if not success:
        print(f"[update_profile_detailed] Error: User not found for user_id: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")

    print(
        f"[update_profile_detailed] Profile updated successfully for user_id: {user_id}"
    )
    return {"message": "Profile updated successfully"}


@router.get("/getUserTickets")
async def get_user_tickets(user_id: int = Depends(get_current_user)):
    print(f"[get_user_tickets] API called with user_id: {user_id}")

    @sync_to_async
    def get_user_tickets_async(user_id):
        print(f"[get_user_tickets_async] Retrieving tickets for user_id: {user_id}")
        user = CustomUser.objects.get(id=user_id)
        tickets = Ticket.objects.filter(user=user)
        print(f"[get_user_tickets_async] Found {tickets.count()} tickets")
        ticket_list = []
        for ticket in tickets:
            # Create serializable event object            # Default location dictionary with all required fields
            default_location = {
                "address": "",
                "city": "",
                "state": "",
                "zip_code": "",
                "country": "",
            }

            # Get event location if available, otherwise use default
            location_data = default_location
            if hasattr(ticket.event, "location") and ticket.event.location:
                # If location is a dictionary, update default values with available ones
                if isinstance(ticket.event.location, dict):
                    location_data = {**default_location, **ticket.event.location}
                # If location is a string or other object, put it in the address field
                elif ticket.event.location:
                    location_data["address"] = str(ticket.event.location)

            event_obj = {
                "eventId": str(ticket.event.eventId),
                "title": ticket.event.title,
                "date": ticket.event.date,
                "start_time": ticket.event.start_time,
                "end_time": ticket.event.end_time,
                "header_photo": (
                    ticket.event.header_photo.url if ticket.event.header_photo else None
                ),
                "description": (
                    ticket.event.description
                    if hasattr(ticket.event, "description")
                    else None
                ),
                "location": location_data,
            }

            ticket_list.append(
                {
                    "ticketId": str(ticket.ticketId),
                    "guestFirstName": ticket.guestFirstName,
                    "guestLastName": ticket.guestLastName,
                    "event": event_obj,  # Include the complete event object
                    "guestEmail": ticket.guestEmail,
                    "eventId": str(ticket.event.eventId),
                    "eventTitle": ticket.event.title,
                    "date": ticket.event.date,
                    "header_photo": (
                        ticket.event.header_photo.url
                        if ticket.event.header_photo
                        else None
                    ),
                    "qrCodeImage": (
                        ticket.qrCodeImage.url if ticket.qrCodeImage else None
                    ),
                    "status": ticket.status,
                    "eventDate": ticket.event.date,
                    "eventStartTime": ticket.event.start_time,
                    "eventEndTime": ticket.event.end_time,
                }
            )

        return ticket_list

    ticket_data = await get_user_tickets_async(user_id)
    tickets = [TicketSerializer(**ticket) for ticket in ticket_data]

    print(f"[get_user_tickets] Returning {len(tickets)} serialized tickets")
    return {"tickets": tickets}


@router.get("/getUserTickets/{ticketId}/details")
async def get_user_ticket_details(
    ticketId: str, user_id: int = Depends(get_current_user)
):
    """
    API endpoint for getting user ticket details.
    Returns details of a specific ticket belonging to the authenticated user.
    """
    print(
        f"[get_user_ticket_details] API called with ticketId: {ticketId}, user_id: {user_id}"
    )

    @sync_to_async
    def get_user_ticket_details_async(ticketId, user_id):
        print(
            f"[get_user_ticket_details_async] Retrieving ticket details for ticketId: {ticketId}, user_id: {user_id}"
        )
        user = CustomUser.objects.get(id=user_id)
        try:
            ticket = Ticket.objects.get(ticketId=ticketId, user=user)
            print(f"[get_user_ticket_details_async] Found ticket with ID: {ticketId}")
            return {
                "ticketId": str(ticket.ticketId),
                "guestFirstName": ticket.guestFirstName,
                "guestLastName": ticket.guestLastName,
                "guestEmail": ticket.guestEmail,
                "eventId": str(ticket.event.eventId),
                "eventTitle": ticket.event.title,
                "date": ticket.event.date,
                "header_photo": (
                    ticket.event.header_photo.url if ticket.event.header_photo else None
                ),
                "qrCodeImage": ticket.qrCodeImage.url if ticket.qrCodeImage else None,
                "status": ticket.status,
            }

        except Ticket.DoesNotExist:
            return None

    ticket_data = await get_user_ticket_details_async(ticketId, user_id)
    if ticket_data is None:
        print(
            f"[get_user_ticket_details] Error: Ticket not found for ticketId: {ticketId}, user_id: {user_id}"
        )
        raise HTTPException(status_code=404, detail="Ticket not found")

    print(f"[get_user_ticket_details] Returning ticket data for ticketId: {ticketId}")
    return ticket_data


@router.get("/profile/favoriteEvents")
async def favoriteEvents(user_id: int = Depends(get_current_user)):
    """
    API endpoint for getting profile overview.
    Returns user profile data.
    """
    print(f"[favoriteEvents] API called with user_id: {user_id}")

    @sync_to_async
    def get_fav_events(user_id):
        try:
            print(f"[get_fav_events] Retrieving favorite events for user_id: {user_id}")
            user = CustomUser.objects.get(id=user_id)
            user_profile = UserProfile.objects.get(user=user)
            events = user_profile.favorite_events.all()
            print(f"[get_fav_events] Found {events.count()} favorite events")
            event_data = [
                {
                    "eventId": event.eventId,
                    "title": event.title,
                    "date": event.date,
                    "header_photo": (
                        event.header_photo.url if event.header_photo else None
                    ),
                }
                for event in events
            ]
            return event_data
        except CustomUser.DoesNotExist or UserProfile.DoesNotExist:
            return None

    events_data = await get_fav_events(user_id)
    if events_data is None:
        print(f"[favoriteEvents] Error: User not found for user_id: {user_id}")
        raise HTTPException(status_code=404, detail="Event not found")
    print(
        f"[favoriteEvents] Returning {len(events_data)} favorite events for user_id: {user_id}"
    )
    return events_data


@router.post("/profile/delete")
async def delete_profile(user_id: int = Depends(get_current_user)):
    """
    API endpoint for deleting a user profile.
    Deletes the user profile and associated data.
    """
    print(f"[delete_profile] API called with user_id: {user_id}")

    @sync_to_async
    def delete_profile(user_id):
        try:
            print(f"[delete_profile] Deleting user with user_id: {user_id}")
            user = CustomUser.objects.get(id=user_id)
            user.delete()
            print(f"[delete_profile] User deleted successfully")
            return True
        except CustomUser.DoesNotExist:
            return False

    success = await delete_profile(user_id)
    if not success:
        print(f"[delete_profile] Error: User not found for user_id: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")

    print(f"[delete_profile] Profile deleted successfully for user_id: {user_id}")
    return {"message": "Profile deleted successfully"}


@router.get("/getUserTransactions")
async def get_user_transactions(user_id: int = Depends(get_current_user)):
    print(f"[get_user_transactions] API called with user_id: {user_id}")

    @sync_to_async
    def get_user_transactions(user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            if not user.customer_id:
                existing_customer = CustomerAccount.searchCustomerAccount(user.email)
                if existing_customer:
                    user.customer_id = existing_customer.id
                    user.save()
                    print(
                        f"[get_user_transactions] Customer ID updated for user_id: {user_id}"
                    )
                else:
                    # Pass None for request if needed
                    new_customer = CustomerAccount.createCustomerAccount(
                        None, user.email, user.first_name, user.last_name
                    )
                    if new_customer:
                        user.customer_id = new_customer.id
                        user.save()
                        print(
                            f"[get_user_transactions] New customer created for user_id: {user_id}"
                        )
                    else:
                        print(
                            f"[get_user_transactions] Error: Unable to create customer account for user_id: {user_id}"
                        )
                        return None
            # Use the same logic as in customerSetup.py: getCustomerTransactions
            # Since we don't have a Django request object, pass None
            transactions = CustomerAccount.getCustomerTransactions(
                None, user.customer_id
            )
            print(
                f"[get_user_transactions] Found {len(transactions)} transactions for user_id: {user_id}"
            )
            transaction_list = []
            for transaction in transactions:
                # transaction is a dict, not an object
                transaction_list.append(
                    {
                        "transactionId": transaction.get("id"),
                        "amount": transaction.get("amount"),
                        "currency": transaction.get("currency"),
                        "description": transaction.get("description"),
                        "created_at": transaction.get("created"),
                        "receipt_url": transaction.get("receipt_url"),
                        "status": transaction.get("status"),
                    }
                )
            return transaction_list
        except CustomUser.DoesNotExist:
            return None

    transactions_data = await get_user_transactions(user_id)
    if transactions_data is None:
        print(f"[get_user_transactions] Error: User not found for user_id: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")
    print(
        f"[get_user_transactions] Returning {len(transactions_data)} transactions for user_id: {user_id}"
    )
    return transactions_data


@router.get("/getUserPaymentMethods")
async def get_user_payment_methods(user_id: int = Depends(get_current_user)):
    print(f"[get_user_payment_methods] API called with user_id: {user_id}")

    @sync_to_async
    def get_user_payment_methods_sync(user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            # Stripe customer setup logic (from profileView)
            if not user.customer_id:
                existing_customer = CustomerAccount.searchCustomerAccount(user.email)
                if existing_customer:
                    user.customer_id = existing_customer.id
                    user.save()
                    print(
                        f"[get_user_payment_methods] Found existing Stripe customer: {existing_customer.id}"
                    )
                else:
                    new_customer = CustomerAccount.createCustomerAccount(
                        None, user.email, user.first_name, user.last_name
                    )
                    if new_customer:
                        user.customer_id = new_customer.id
                        user.save()
                        print(
                            f"[get_user_payment_methods] Created new Stripe customer: {new_customer.id}"
                        )
                    else:
                        print(
                            "[get_user_payment_methods] Failed to create Stripe customer"
                        )
                        return None

            payment_methods = CustomerAccount.listPaymentMethods(user.customer_id)
            if payment_methods:
                for method in payment_methods:
                    # Convert exp_month to month name (e.g., 5 -> May)
                    try:
                        method["exp_month"] = datetime.strptime(
                            str(method["exp_month"]), "%m"
                        ).strftime("%B")
                    except Exception:
                        pass
                return payment_methods
            else:
                return []
        except CustomUser.DoesNotExist:
            print(
                f"[get_user_payment_methods] Error: User with id {user_id} does not exist"
            )
            return None
        except Exception as e:
            print(f"[get_user_payment_methods] Unexpected error: {str(e)}")
            return None

    payment_methods_data = await get_user_payment_methods_sync(user_id)
    if payment_methods_data is None:
        print(
            f"[get_user_payment_methods] Error: User not found for user_id: {user_id}"
        )
        raise HTTPException(status_code=404, detail="User not found")
    print(
        f"[get_user_payment_methods] Returning {len(payment_methods_data)} payment methods for user_id: {user_id}"
    )
    return payment_methods_data


@router.post("/payment/deletePaymentMethod")
async def delete_payment_method(
    request: Request,
    user_id: int = Depends(get_current_user),
    paymentMethodId: str = Body(..., embed=True),
):
    """Delete a payment method for the current user."""

    @sync_to_async
    def get_user(user_id):
        return CustomUser.objects.get(id=user_id)

    user = await get_user(user_id)
    if paymentMethodId:
        CustomerAccount.removePaymentMethod(None, paymentMethodId)
        return {"success": True, "message": "Payment method deleted successfully."}
    else:
        raise HTTPException(status_code=400, detail="Invalid payment method ID.")


@router.post("/payment/setDefaultPaymentMethod")
async def set_default_payment_method(
    request: Request,
    user_id: int = Depends(get_current_user),
    paymentMethodId: str = Body(..., embed=True),
):
    """Set a default payment method for the current user."""

    @sync_to_async
    def get_user(user_id):
        return CustomUser.objects.get(id=user_id)

    user = await get_user(user_id)
    if paymentMethodId:
        success = CustomerAccount.setDefaultPaymentMethod(
            user.customer_id, paymentMethodId
        )
        if success:
            return {
                "success": True,
                "message": "Default payment method set successfully.",
            }
        else:
            raise HTTPException(
                status_code=400, detail="Failed to set default payment method."
            )
    else:
        raise HTTPException(status_code=400, detail="Invalid payment method ID.")


@router.post("/payment/addPayoutMethodToProfile")
async def add_payout_method_to_profile(
    request: Request, user_id: int = Depends(get_current_user)
):
    """Add a payout (bank) method to the user's profile."""

    @sync_to_async
    def get_user(user_id):
        return CustomUser.objects.get(id=user_id)

    user = await get_user(user_id)
    bank = CustomerAccount.setupBankAccount(None, user.customer_id)
    if bank:
        return {"success": True, "message": "Bank account added successfully."}
    else:
        raise HTTPException(status_code=400, detail="Failed to add bank account.")


@router.post("/payment/requestInstantPayout")
async def request_instant_payout(
    request: Request, user_id: int = Depends(get_current_user)
):
    """Request an instant payout for the user if eligible."""

    @sync_to_async
    def get_user(user_id):
        return CustomUser.objects.get(id=user_id)

    user = await get_user(user_id)
    from stripeManagementApp.getEarnings import GetEarnings

    accountBalance = GetEarnings.getStripeAccountBalance(user.connectAccountID)
    if not accountBalance:
        raise HTTPException(
            status_code=400, detail="Could not retrieve account balance."
        )
    available_balance = accountBalance.get("available", 0)
    if available_balance < 1:
        raise HTTPException(
            status_code=400, detail="Insufficient balance for a payout."
        )
    payout = GetEarnings.requestPayout(
        user.connectAccountID, int(available_balance * 100)
    )
    if payout:
        return {"success": True, "message": "Payout requested successfully."}
    else:
        raise HTTPException(status_code=400, detail="Failed to process payout.")


@router.get("/checkHost")
async def check_host(user_id: int = Depends(get_current_user)):
    print(f"[check_host] API called with user_id: {user_id}")

    @sync_to_async
    def check_user_is_host(user_id):
        try:
            print(f"[check_user_is_host] Checking if user_id: {user_id} is a host")
            user = CustomUser.objects.get(id=user_id)
            is_host = user.groups.filter(name="Host").exists()
            print(f"[check_user_is_host] User is host: {is_host}")
            return {"is_host": is_host}
        except CustomUser.DoesNotExist:
            return None

    result = await check_user_is_host(user_id)
    if result is None:
        print(f"[check_host] Error: User not found for user_id: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")
    print(f"[check_host] Returning host status for user_id: {user_id}: {result}")
    return result


@router.get("/getHostDashboardLink")
async def get_host_dashboard_link(user_id: int = Depends(get_current_user)):
    """
    API endpoint for getting Stripe dashboard link for hosts.
    Returns a link to the Stripe dashboard for the user's connected account.
    """
    print(f"[get_host_dashboard_link] API called with user_id: {user_id}")

    @sync_to_async
    def get_host_stripe_link(user_id):
        try:
            print(
                f"[get_host_stripe_link] Retrieving Stripe dashboard link for user_id: {user_id}"
            )
            user = CustomUser.objects.get(id=user_id)

            # Check if stripe account ID exists
            if not user.connectAccountID:
                print(
                    f"[get_host_stripe_link] No connectAccountID found for user_id: {user_id}"
                )
                return {
                    "error": "You aren't a host yet. Host your first event to get started."
                }, 400

            # Import stripe here to avoid loading it unnecessarily
            import stripe
            from django.conf import settings

            stripe.api_key = settings.STRIPE_SECRET_KEY

            # Create the stripe login link
            try:
                stripe_login_link = stripe.Account.create_login_link(
                    user.connectAccountID
                )
                return {"url": stripe_login_link.url}, 200
            except Exception as e:
                print(f"Stripe error: {str(e)}")
                return {"error": f"Failed to get Stripe account link: {str(e)}"}, 400

        except CustomUser.DoesNotExist:
            return None

    result, status_code = await get_host_stripe_link(user_id)
    if result is None:
        print(f"[get_host_dashboard_link] Error: User not found for user_id: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")

    if status_code != 200:
        print(
            f"[get_host_dashboard_link] Error: {result.get('error')} for user_id: {user_id}"
        )
        raise HTTPException(status_code=status_code, detail=result.get("error"))

    print(f"[get_host_dashboard_link] Returning dashboard link for user_id: {user_id}")
    return result


@router.get("/getUserCollege")
async def get_user_college(user_id: int = Depends(get_current_user)):
    """
    API endpoint for getting user's college information.
    Returns the college name and ID associated with the user.
    """
    print(f"[get_user_college] API called with user_id: {user_id}")

    @sync_to_async
    def get_user_college(user_id):
        try:
            print(f"[get_user_college] Retrieving college info for user_id: {user_id}")
            user = CustomUser.objects.get(id=user_id)
            college = user.user_profile.college
            print(f"[get_user_college] College found: {college is not None}")
            if college:
                return {
                    "collegeId": str(college.collegeId),
                    "collegeName": college.name,
                }
            else:
                return None
        except CustomUser.DoesNotExist:
            return None

    college_data = await get_user_college(user_id)
    if college_data is None:
        print(
            f"[get_user_college] Error: User or college not found for user_id: {user_id}"
        )
        raise HTTPException(status_code=404, detail="User not found")

    print(
        f"[get_user_college] Returning college data for user_id: {user_id}: {college_data}"
    )
    return college_data


@router.get("/settings")
async def get_user_settings(user_id: int = Depends(get_current_user)):
    """
    API endpoint for retrieving user settings and profile information.
    Returns user profile data and settings.
    """
    print(f"[get_user_settings] API called with user_id: {user_id}")

    @sync_to_async
    def get_settings_async(user_id):
        try:
            print(
                f"[get_settings_async] Retrieving user settings for user_id: {user_id}"
            )
            user = CustomUser.objects.get(id=user_id)
            profile = get_object_or_404(UserProfile, user=user)

            user_serializer = CustomUserSerializer(user)
            profile_serializer = UserProfileSerializer(profile)
            print(f"[get_settings_async] User and profile data serialized successfully")

            return {
                "user": user_serializer.data,
                "profile": profile_serializer.data,
            }
        except CustomUser.DoesNotExist:
            return None
        except Exception as e:
            error_trace = traceback.format_exc()
            print(
                f"[get_user_settings] Unexpected error retrieving settings for user_id {user_id}: {str(e)}\n{error_trace}"
            )
            return None

    try:
        settings_data = await get_settings_async(user_id)
        if settings_data is None:
            raise HTTPException(status_code=404, detail="User not found")
        return settings_data
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print(f"[get_user_settings] Unhandled exception: {str(e)}\n{error_trace}")
            raise HTTPException(status_code=500, detail="Internal server error")
        raise e


@router.post("/settings")
async def update_user_settings(
    request: Request,
    user_id: int = Depends(get_current_user),
):
    """
    API endpoint for updating user settings and profile information.
    Updates user profile data based on the action provided.
    """
    print(f"[update_user_settings] API called with user_id: {user_id}")
    # Check content type and handle accordingly
    content_type = request.headers.get("content-type", "")
    print("[update_user_settings] Content type:", content_type)

    # Initialize data dict
    data = {}
    files = {}

    try:
        if "application/json" in content_type:
            # Handle JSON request
            json_data = await request.json()
            print("[update_user_settings] JSON data:", json_data)
            data = json_data

            # Handle profile photo in JSON format (React Native)
            action = data.get("action")
            if action == "updateProfilePicture" and "profile_photo" in data:
                # Extract the profile_photo data
                profile_photo_data = data.pop("profile_photo", None)
                if profile_photo_data and isinstance(profile_photo_data, dict):
                    print("[update_user_settings] Photo:", profile_photo_data)
                    # Special handling in update_settings_async
                    data["profile_photo_json"] = profile_photo_data
        else:
            # Handle form data request
            form_data = await request.form()
            print("[update_user_settings] Form data:", form_data.keys())

            # Log all form data items for debugging
            for key, value in form_data.items():
                print("[update_user_settings] Form item:", key, type(value))
                if hasattr(value, "filename"):
                    print("[update_user_settings] File:", key, value.filename)
                    # This is a file upload
                    files[key] = value
                else:
                    # This is regular form data
                    data[key] = value
    except Exception as e:
        error_trace = traceback.format_exc()
        print("[update_user_settings] Error:", str(e), "\n", error_trace)
        raise HTTPException(
            status_code=400, detail={"error": f"Invalid request data: {str(e)}"}
        )

    # Extract action from data
    action = data.get("action")
    if not action:
        raise HTTPException(
            status_code=400, detail={"error": "Missing required parameter: action"}
        )

    @sync_to_async
    def update_settings_async(user_id, action, form_data, files=None):
        try:
            print(
                f"[update_settings_async] Processing settings update for user_id: {user_id}, action: {action}"
            )
            user = CustomUser.objects.get(id=user_id)
            profile = get_object_or_404(UserProfile, user=user)
            print(f"[update_settings_async] User and profile retrieved successfully")

            if action == "updateProfilePicture":
                print("[update_settings_async] Action: updateProfilePicture")
                print("[update_settings_async] Files:", files)
                print("[update_settings_async] Form keys:", form_data.keys())

                # Check for standard file upload
                if files and "profile_photo" in files:
                    print("[update_settings_async] Standard file upload")

                    # Create Django-compatible files dict
                    django_files = {}
                    upload_file = files["profile_photo"]

                    # Read file content
                    file_content = upload_file.file.read()

                    # Import here to avoid circular imports
                    from django.core.files.base import ContentFile

                    # Create ContentFile object
                    django_files["profile_photo"] = ContentFile(
                        file_content, name=upload_file.filename
                    )

                    # Create and validate form with proper file data
                    form = UpdateProfilePhotoForm(
                        form_data, django_files, instance=profile
                    )

                    if form.is_valid():
                        updated_profile = form.save()
                        serializer = UserProfileSerializer(updated_profile)
                        print(
                            f"[update_settings_async] Profile picture updated successfully"
                        )
                        return {
                            "message": "Profile picture updated successfully!",
                            "profile": serializer.data,
                        }
                    print("[update_settings_async] Validation errors:", form.errors)
                    return {"errors": form.errors, "status_code": 400}

                # Handle React Native style file upload (as JSON data)
                elif "profile_photo_json" in form_data:
                    print("[update_settings_async] React Native upload")
                    file_data = form_data["profile_photo_json"]

                    # Check if it's properly structured
                    if isinstance(file_data, dict) and "uri" in file_data:
                        try:
                            import requests
                            from django.core.files.base import ContentFile
                            from tempfile import NamedTemporaryFile

                            # Get the file URI from React Native
                            file_uri = file_data.get("uri")
                            default = "profile_photo.jpg"
                            file_name = file_data.get("name") or default

                            print("[update_settings_async] Download from:", file_uri)

                            # For local file URIs we need a different approach
                            if file_uri.startswith(("http://", "https://")):
                                # Download the image from the URI
                                response = requests.get(file_uri, stream=True)
                                if response.status_code == 200:
                                    # Create a temporary file
                                    img_temp = NamedTemporaryFile(delete=True)
                                    for chunk in response.iter_content(1024):
                                        img_temp.write(chunk)

                                    # Save the profile photo
                                    img_temp.seek(0)
                                    profile.profile_photo.save(
                                        file_name,
                                        ContentFile(img_temp.read()),
                                        save=True,
                                    )
                                    serializer = UserProfileSerializer(profile)
                                    return {
                                        "message": "Profile picture updated!",
                                        "profile": serializer.data,
                                    }
                            else:
                                return {
                                    "error": "Cannot process file URI",
                                    "status_code": 400,
                                }
                        except Exception as e:
                            print("[update_settings_async] URI error:", str(e))
                            return {
                                "error": f"Failed to process upload: {str(e)}",
                                "status_code": 400,
                            }

                # Handle case where profile_photo isn't processed as a file
                elif "profile_photo" in form_data and not isinstance(
                    form_data["profile_photo"], dict
                ):
                    print("[update_settings_async] Not processed as file")
                    return {
                        "error": "Photo not recognized as file. "
                        "Check form encoding.",
                        "status_code": 400,
                    }

                # Handle JSON-based profile photo metadata from web client
                elif "profile_photo" in form_data and isinstance(
                    form_data["profile_photo"], dict
                ):
                    print("[update_settings_async] Metadata without file")
                    return {
                        "error": "Invalid upload. Use multipart/form-data.",
                        "status_code": 400,
                    }

                else:
                    print("[update_settings_async] No photo in request")
                    return {
                        "error": "No profile photo found in the request",
                        "status_code": 400,
                    }

            elif action == "updatePersonalInfo":
                print(f"[update_settings_async] Action: updatePersonalInfo")
                form = UpdatePersonalInfo(form_data, instance=user)
                if form.is_valid():
                    updated_user = form.save()
                    serializer = CustomUserSerializer(updated_user)
                    print(f"[update_settings_async] Personal info updated successfully")
                    return {
                        "message": "Personal info updated!",
                        "user": serializer.data,
                    }
                print(f"[update_settings_async] Form validation errors: {form.errors}")
                return {"errors": form.errors, "status_code": 400}

            elif action == "updateContactInfo":
                print(f"[update_settings_async] Action: updateContactInfo")
                form = UpdateContactInfo(form_data, instance=user)
                if form.is_valid():
                    updated_user = form.save()
                    serializer = CustomUserSerializer(updated_user)
                    print(f"[update_settings_async] Contact info updated successfully")
                    return {
                        "message": "Contact info updated!",
                        "user": serializer.data,
                    }
                print(f"[update_settings_async] Form validation errors: {form.errors}")
                return {"errors": form.errors, "status_code": 400}

            else:
                print(f"[update_settings_async] Invalid action: {action}")
                return {"error": "Invalid action.", "status_code": 400}

        except CustomUser.DoesNotExist:
            return {"error": "User not found", "status_code": 404}
        except Exception as e:
            error_trace = traceback.format_exc()
            print(
                "[update_settings_async] Error for user:", user_id, str(e), error_trace
            )
            return {"error": f"Error: {str(e)}", "status_code": 500}

    try:
        # Process with form data and files from earlier parsing
        print(
            f"[update_user_settings] Calling update_settings_async with action: {action}"
        )
        result = await update_settings_async(user_id, action, data, files)
        if "status_code" in result:
            status_code = result.pop("status_code")
            print(
                f"[update_user_settings] Error with status code {status_code}: {result}"
            )
            raise HTTPException(status_code=status_code, detail=result)

        print(
            f"[update_user_settings] Successfully processed action '{action}' for user_id: {user_id}"
        )
        print(f"[update_user_settings] Returning result: {result}")
        return result
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_trace = traceback.format_exc()
            print("[update_user_settings] Exception:", str(e), error_trace)
            raise HTTPException(status_code=500, detail="Internal server error")
        raise e
