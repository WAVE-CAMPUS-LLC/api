from datetime import datetime
import time
import json
import stripe
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.shortcuts import get_object_or_404
from .models import UserProfile
from blogApp.models import Blog
from eventTicketsApp.models import Ticket
from stripeManagementApp.customerSetup import CustomerAccount, ConnectAccount
from stripeManagementApp.getEarnings import GetEarnings
from .serializers import UserProfileSerializer
from authenticationApp.serializers import CustomUserSerializer
from eventManagementApp.serializers import EventSerializer
from eventManagementApp.models import Event
from .forms import (
    UpdateContactInfo,
    UpdatePersonalInfo,
    UpdateProfilePhotoForm,
)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def profile_api(request):
    """API endpoint for retrieving user profile details and managing payment methods"""
    
    user = request.user
    purchased_tickets = Ticket.objects.filter(user=user).select_related('event')
    blog_items = Blog.objects.filter(created_by=user)
    user_profile = get_object_or_404(UserProfile, user=user)
    favorite_events = user_profile.favorite_events.all()
    
    transactions = CustomerAccount.getCustomerTransactions(request, user.customer_id)
    account_balance = GetEarnings.getStripeAccountBalance(user.connectAccountID)
    total_earnings = GetEarnings.getTotalEarnings(user.connectAccountID)

    # Get payment methods and format expiration month
    payment_methods = CustomerAccount.listPaymentMethods(user.customer_id)
    if payment_methods:
        for method in payment_methods:
            method["exp_month"] = datetime.strptime(str(method["exp_month"]), "%m").strftime("%B")

    dashboard_link = ConnectAccount.getStripeAccountLogin(request, user) if user.connectAccountID else None
    can_see_payouts = dashboard_link and user.groups.filter(name='Host').exists()

    if request.method == "POST":
        action = request.data.get("action")

        try:
            if action == "deletePaymentMethod":
                payment_method_id = request.data.get("paymentMethodId")
                if payment_method_id:
                    CustomerAccount.removePaymentMethod(request, payment_method_id)
                    return Response({"message": "Payment method deleted successfully."}, status=status.HTTP_200_OK)
                return Response({"error": "Invalid payment method ID."}, status=status.HTTP_400_BAD_REQUEST)

            elif action == "setDefaultPaymentMethod":
                payment_method_id = request.data.get("paymentMethodId")
                if payment_method_id:
                    success = CustomerAccount.setDefaultPaymentMethod(user.customer_id, payment_method_id)
                    return Response({"message": "Default payment method set successfully." if success else "Failed to set default payment method."},
                                    status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST)

            elif action == "addPayoutMethodToProfile":
                bank = CustomerAccount.setupBankAccount(request, user.customer_id)
                return Response({"message": "Bank account added successfully." if bank else "Failed to add bank account."},
                                status=status.HTTP_200_OK if bank else status.HTTP_400_BAD_REQUEST)

            elif action == "requestInstantPayout":
                available_balance = account_balance["available"]
                if available_balance < 1:
                    return Response({"error": "Insufficient balance for a payout."}, status=status.HTTP_400_BAD_REQUEST)

                payout = GetEarnings.requestPayout(user.connectAccountID, int(available_balance * 100))
                return Response({"message": "Payout requested successfully." if payout else "Failed to process payout."},
                                status=status.HTTP_200_OK if payout else status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    response_data = {
        "blogItems": [{"id": b.blogId, "title": b.title} for b in blog_items],
        "userProfile": {"username": user.username, "email": user.email, "first_name": user.first_name, "last_name": user.last_name, "profilePic": user_profile.profile_photo.url},
        "favoriteEvents": [{"id": e.eventId, "title": e.title} for e in favorite_events],
        "payments": payment_methods if payment_methods else None,
        "purchasedTickets": [{"event": t.event.title, "date": t.event.date} for t in purchased_tickets],
        "accountBalance": account_balance,
        "totalEarnings": total_earnings,
        "dashboardLink": dashboard_link,
        "transactions": transactions,
        "canSeePayouts": can_see_payouts,
    }
    
    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def settings_api(request):
    """API endpoint for retrieving and updating user settings and profile information"""
    
    user = request.user
    profile = get_object_or_404(UserProfile, user=user)
    
    if request.method == "POST":
        action = request.data.get("action")
        
        try:
            if action == "updateProfilePicture":
                form = UpdateProfilePhotoForm(request.data, request.FILES, instance=profile)
                if form.is_valid():
                    updated_profile = form.save()
                    serializer = UserProfileSerializer(updated_profile)
                    return Response({
                        "message": "Profile picture updated successfully!",
                        "profile": serializer.data
                    }, status=status.HTTP_200_OK)
                return Response({"errors": form.errors}, status=status.HTTP_400_BAD_REQUEST)
                
            elif action == "updatePersonalInfo":
                form = UpdatePersonalInfo(request.data, instance=user)
                if form.is_valid():
                    updated_user = form.save()
                    serializer = CustomUserSerializer(updated_user)
                    return Response({
                        "message": "Personal information updated successfully!",
                        "user": serializer.data
                    }, status=status.HTTP_200_OK)
                return Response({"errors": form.errors}, status=status.HTTP_400_BAD_REQUEST)
                
            elif action == "updateContactInfo":
                form = UpdateContactInfo(request.data, instance=user)
                if form.is_valid():
                    updated_user = form.save()
                    serializer = CustomUserSerializer(updated_user)
                    return Response({
                        "message": "Contact information updated successfully!",
                        "user": serializer.data
                    }, status=status.HTTP_200_OK)
                return Response({"errors": form.errors}, status=status.HTTP_400_BAD_REQUEST)
                
            else:
                return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # For GET requests, return the user's current settings using serializers
    user_serializer = CustomUserSerializer(user)
    profile_serializer = UserProfileSerializer(profile)
    
    response_data = {
        "user": user_serializer.data,
        "profile": profile_serializer.data,
    }
    
    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def favourited_events_api(request):
    user = request.user
    profile = get_object_or_404(UserProfile, user=user)
    favourite_events = profile.favorite_events.all()
    
    favourite_events_serialized = EventSerializer(favourite_events, many=True)
    
    return Response(favourite_events_serialized.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_methods_api(request):
    user = request.user
    customer_id = user.customer_id
    payment_methods = CustomerAccount.listPaymentMethods(customer_id)
    if payment_methods:
        for method in payment_methods:
            method["exp_month"] = datetime.strptime(str(method["exp_month"]), "%m").strftime("%B")
    
    return Response({
        "payment_methods": payment_methods or [],
        "has_payment_methods": bool(payment_methods)
    }, status=status.HTTP_200_OK)
