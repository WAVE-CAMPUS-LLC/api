from datetime import datetime
import time
import json
import stripe

from http.client import HTTPResponse
from django.http import Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from .forms import (
    UserProfileForm,
    UpdateContactInfo,
    UpdatePersonalInfo,
    EditUserProfileForm,
    UpdateProfilePhotoForm,
)
from django.contrib.auth.models import Group
from .models import UserProfile, EventTypePreferences
from authenticationApp.models import CustomUser
from stripeManagementApp.customerSetup import CustomerAccount, ConnectAccount
from stripeManagementApp.getEarnings import GetEarnings
from eventTicketsApp.models import Ticket
# Decorators to check user roles and permissions
from wave_v1.decorators import check_suspension, member, verified, onboarded
from blogApp.models import Blog

UserModel = get_user_model()


# Create your views here.
@login_required(login_url="authentication:login")
@check_suspension
@member
@verified
def profileView(request):
    userRequest = request.user
    purchased_tickets = Ticket.objects.filter(user=request.user).select_related('event')
    blogItems = Blog.objects.filter(created_by=userRequest)
    userProfile = UserProfile.objects.get(user=userRequest)
    favorite_events = userProfile.favorite_events.all()
    stripeKey = settings.STRIPE_PUBLISHABLE_KEY
    
    transactions = CustomerAccount.getCustomerTransactions(request, userRequest.customer_id)
    
    accountBalance = GetEarnings.getStripeAccountBalance(userRequest.connectAccountID)
    totalEarnings = GetEarnings.getTotalEarnings(userRequest.connectAccountID)

    payment_methods = CustomerAccount.listPaymentMethods(userRequest.customer_id)
    for method in payment_methods:
        method["exp_month"] = datetime.strptime(
            str(method["exp_month"]), "%m"
        ).strftime("%B")
        
    siteDomain = settings.SITE_URL

    link = request.build_absolute_uri(reverse("accountManagement:userAccount"))

    if userRequest.connectAccountID:
        dashboardLink = ConnectAccount.getStripeAccountLogin(request, userRequest, siteDomain, link)
    else:
        dashboardLink = None
            
    if request.method == "POST":
        action = request.POST.get("action")

        try:
            if action == "deletePaymentMethod":
                payment_method_id = request.POST.get("paymentMethodId")
                if payment_method_id:
                    CustomerAccount.removePaymentMethod(request, payment_method_id)
                    messages.success(request, "Payment method deleted successfully.")
                else:
                    messages.error(request, "Invalid payment method ID.")
            elif action == "setDefaultPaymentMethod":
                payment_method_id = request.POST.get("paymentMethodId")
                if payment_method_id:
                    success = CustomerAccount.setDefaultPaymentMethod(
                        userRequest.customer_id, payment_method_id
                    )
                    if success:
                        messages.success(
                            request, "Default payment method set successfully."
                        )
                    else:
                        messages.error(request, "Failed to set default payment method.")
                else:
                    messages.error(request, "Invalid payment method ID.")
                    
            elif action == "addPayoutMethodToProfile":
                bank = CustomerAccount.setupBankAccount(request, userRequest.customer_id)
                if bank:
                    messages.success(request, "Bank account added successfully.")
                else:
                    messages.error(request, "Failed to add bank account.")
        
            elif action == "requestInstantPayout":
                available_balance = accountBalance["available"]
                if available_balance < 1:  # If balance is too low for a payout
                    messages.error(request, "Insufficient balance for a payout.")
                    return redirect("accountManagement:userAccount")

                payout = GetEarnings.requestPayout(userRequest.connectAccountID, int(available_balance * 100))
                if payout:
                    messages.success(request, "Payout requested successfully.")
                else:
                    messages.error(request, "Failed to process payout.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
        finally:
            return redirect("accountManagement:userAccount")

    return render(
        request,
        "accountManagementApp/profileOverview.html",
        {
            "blogItems": blogItems,
            "userRequest": userRequest,
            "userProfile": userProfile,
            "favoriteEvents": favorite_events,
            "stripeKey": stripeKey,
            "payments": payment_methods,
            "purchasedTickets": purchased_tickets,
            "accountBalance": accountBalance,
            "totalEarnings": totalEarnings,
            "dashboardLink": dashboardLink,
            "transactions": transactions,
        },
    )


def addCard(request):
    try:
        user = request.user
        userAccount = CustomUser.objects.get(username=user.username)
        customer_id = userAccount.customer_id

        data = json.loads(request.body)
        token = data.get("token")

        if not token:
            messages.error(request, "No token provided")
            return JsonResponse({"success": False})

        # Retrieve the payment method details using the token
        payment_method = stripe.PaymentMethod.create(
            type="card",
            card={"token": token},
        )

        # Check if the card already exists
        if CustomerAccount.cardExists(customer_id, payment_method.card.fingerprint):
            messages.error(request, "This card already exists.")
            return JsonResponse({"success": False})

        # Attach the payment method to the customer
        stripe.PaymentMethod.attach(payment_method.id, customer=customer_id)

        # Optionally set the new payment method as the default
        stripe.Customer.modify(
            customer_id,
            invoice_settings={"default_payment_method": payment_method.id},
        )

        messages.success(request, "Payment method added successfully.")
        return JsonResponse({"success": True})
    except stripe.error.StripeError as e:
        messages.error(request, f"Stripe error: {e.user_message}")
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
    return JsonResponse({"success": False})


@login_required(login_url="authentication:login")
@check_suspension
@member
@verified
def profilePreferences(request):
    user = request.user
    profile = UserProfile.objects.get(user=user)
    userModel = CustomUser.objects.get(username=user.username)
    profile_form = UserProfileForm(instance=profile)

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=profile)

        if form.is_valid():
            # Access cleaned_data after form validation
            user.user_preferences_completed = True
            event_types = request.POST.getlist("event_types")  # Get list from POST
            profile.save(event_types=event_types)

            form.save()
            messages.success(request, "Profile preferences updated successfully!")
            userModel.is_onboarded = True
            member_group, _ = Group.objects.get_or_create(name="Member")
            unverified_group, _ = Group.objects.get_or_create(name="Unverified")
            verified_group, _ = Group.objects.get_or_create(name="Verified")
            unboarded_group, _ = Group.objects.get_or_create(name="Unboarded")
            onboarded_group, _ = Group.objects.get_or_create(name="Onboarded")

            userModel.groups.add(member_group)
            userModel.groups.add(verified_group)
            userModel.groups.add(onboarded_group)
            userModel.groups.remove(unverified_group)
            userModel.groups.remove(unboarded_group)
            userModel.save()

            return redirect("accountManagement:userAccount")

    return render(
        request,
        "accountManagementApp/extras/preferences.html",
        {"updateUserProfileForm": profile_form, "user": user, "profile": profile},
    )


@login_required(login_url="authentication:login")
@check_suspension
@member
@verified
def userProfileProcessing(request, username):
    if request.method == "POST":

        custom_user = get_object_or_404(CustomUser, username=username)
        user = get_object_or_404(UserProfile, user=custom_user)

        # Update fields with error handling
        profile_photo = request.FILES.get("profile_photo")
        if profile_photo:
            user.profile_photo = profile_photo

        user.status = request.POST.get("status", "")
        user.gender = request.POST.get("gender", "")
        user.home_state = request.POST.get("home_state", "")
        user.instagram = request.POST.get("instagram", "")
        user.tiktok = request.POST.get("tiktok", "")
        user.college_name = request.POST.get("college_name", "")
        user.major = request.POST.get("major", "")
        graduation_year = request.POST.get("graduation_year", "")
        if graduation_year:
            try:
                # Convert to an integer if a valid value is provided
                graduation_year = int(graduation_year)
            except ValueError:
                graduation_year = None

        # Ensure eventTypes is passed as a list and update it
        event_types = request.POST.getlist("eventTypes", [])
        if event_types:
            event_type_objs = [
                EventTypePreferences.objects.get_or_create(name=et)[0]
                for et in event_types
            ]
            user.event_types.set(event_type_objs)

        # Save updates
        user.save()

        return JsonResponse(
            {"success": True, "message": "Profile updated successfully!"}
        )

    return JsonResponse({"error": True, "message": "Invalid request."}, status=400)


@login_required(login_url="authentication:login")
@check_suspension
@member
@verified
def settingsView(request):
    user = request.user
    personal_form = UpdatePersonalInfo(instance=user)
    profile = UserProfile.objects.get(user=user)
    contact_form = UpdateContactInfo(instance=user)
    editProfileForm = EditUserProfileForm(instance=profile)
    editProfilePictureForm = UpdateProfilePhotoForm(instance=profile)

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "profile-picture":
            form = UpdateProfilePhotoForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, "Profile picture updated successfully!")
        elif form_type == "personal-info":
            form = UpdatePersonalInfo(request.POST, instance=user)
            if form.is_valid():
                form.save()
                messages.success(request, "Personal information updated successfully!")
        elif form_type == "email-info":
            form = UpdateContactInfo(request.POST, instance=user)
            if form.is_valid():
                form.save()
                messages.success(request, "Contact information updated successfully!")
        elif form_type == "phone-info":
            form = UpdateContactInfo(request.POST, instance=user)
            if form.is_valid():
                form.save()
                messages.success(request, "Contact information updated successfully!")

        elif form_type == "profile-info":
            editProfileForm = EditUserProfileForm(request.POST, instance=profile)

            if editProfileForm.is_valid():
                editProfileForm.save()
                messages.success(request, "Profile information updated successfully!")
            else:
                messages.error(request, f"Invalid form {editProfileForm.errors}")
                return redirect("accountManagement:userSettings")
        else:
            messages.error(request, "Invalid form.")
            return redirect("accountManagement:userSettings")

        return redirect("accountManagement:userSettings")

    return render(
        request,
        "accountManagementApp/profileSettings.html",
        {
            "personal_form": personal_form,
            "editProfilePictureForm": editProfilePictureForm,
            "contact_form": contact_form,
            "user": user,
            "profile": profile,
            "editProfileForm": editProfileForm,
        },
    )


from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth import update_session_auth_hash


class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    template_name = "accountManagementApp/partials/passwordChange.html"
    success_message = "Password successfully changed!"

    def post(self, request, *args, **kwargs):
        result = super().post(request, *args, **kwargs)

        if result.status_code == 302:
            update_session_auth_hash(request, request.user)

        return result

    success_url = reverse_lazy("accountManagement:userAccount")
