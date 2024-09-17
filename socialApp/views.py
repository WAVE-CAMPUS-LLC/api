from http.client import HTTPResponse
import re
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from accountManagementApp.models import UserProfile
from django.contrib import messages
from socialApp.models import FriendRequest
from django.db.models import Q

# Decorators to check user roles and permissions
from wave_v1.decorators import member_required, check_suspension

UserModel = get_user_model()


# Create your views here.
@login_required
def socialHomeView(request):
    
    
    pending_friend_requests  = FriendRequest.objects.filter(receiver=request.user, status="pending")
    friends = FriendRequest.objects.filter(Q(sender=request.user) | Q(receiver=request.user), status="accepted")
    
    
    if request.method == "POST":
        action = request.POST.get('action')
        friend_request_id = request.POST.get('friend_request_id')
        
        try:
            friend_request = FriendRequest.objects.get(requestId=friend_request_id, receiver=request.user)

            if action == 'acceptRequest':
                friend_request.acceptRequest()
                messages.success(request, "Friend request accepted.")
            
            elif action == 'declineRequest':
                friend_request.declineRequest()
                messages.success(request, "Friend request declined.")


        except FriendRequest.DoesNotExist:
            messages.warning(request, "Friend request not found.")
            
            
    return render(request, "socialApp/socialHome.html", {'pending_friend_requests': pending_friend_requests, 'friends': friends})


def publicProfileView(request, username):
    try:
        user = get_object_or_404(UserModel, username=username)
        # Ensure user_profile exists or create it if it doesn't
        user_profile, created = UserProfile.objects.get_or_create(user=user)

        friend_request = FriendRequest.objects.filter(
            (Q(sender=request.user) & Q(receiver=user))
            | (Q(sender=user) & Q(receiver=request.user))
        ).first()

        friend_request_status = None
        if friend_request:
            friend_request_status = friend_request.status
            
        is_profile = request.user == user

        if request.method == "POST":
            action = request.POST.get("action")
            if action == "send_request":
                success, message = send_friend_request(request.user, user_profile)

                if success:
                    messages.success(request, message)
                    return redirect("social:publicProfile", username=username)
                else:
                    messages.warning(request, message)
                    return redirect("social:publicProfile", username=username)
            elif (
                action == "cancel_request"
                and friend_request
                and friend_request_status == "pending"
            ):
                friend_request.delete()
                messages.success(request, "Friend request canceled.")
                friend_request_status = None
                return redirect("social:publicProfile", username=username)
            
            elif (
                action == "remove_request"
                and friend_request
                and friend_request_status == "accepted"
            ):
                friend_request.delete()
                messages.success(request, "Friend removed.")
                friend_request_status = None
                return redirect("social:publicProfile", username=username)

    except Http404:
        return render(request, "extras/invalid/invalid.html")

    return render(
        request,
        "socialApp/publicProfile.html",
        {
            "user": user,
            "user_profile": user_profile,
            "friend_request_status": friend_request_status,
            "is_profile": is_profile,
        },
    )


def send_friend_request(sender, receiver_username):
    receiver = get_object_or_404(UserProfile, user__username=receiver_username)

    # First check if there's already an accepted friendship
    if sender.user_profile.is_friends_with(receiver.user):
        return False, "You are already friends."

    # Check if there is already a pending request between these two users
    if sender.user_profile.has_pending_request(receiver.user):
        return False, "A friend request is already pending."

    # Create a new friend request if none exists
    friend_request, created = FriendRequest.objects.get_or_create(
        sender=sender, receiver=receiver.user, defaults={"status": "pending"}
    )

    if not created:
        return False, "Friend request has already been sent."

    return True, "Friend request sent successfully."


@login_required
def accept_friend_request(receiver, sender_username):
    sender = get_object_or_404(UserProfile, user__username=sender_username)

    try:
        friend_request = FriendRequest.objects.get(
            sender=sender.user, receiver=receiver.user, status="pending"
        )
        friend_request.status = "accepted"
        friend_request.save()

        receiver.friends.add(sender.user)
        sender.friends.add(receiver.user)

        return True, "Friend request accepted"

    except FriendRequest.DoesNotExist:
        return False, "No pending request found"
