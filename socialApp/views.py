from channels.layers import get_channel_layer
import random
from datetime import datetime
from asgiref.sync import async_to_sync
from ssl import MemoryBIO
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.conf import settings
from django.urls import reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.template import RequestContext
from django.template.loader import render_to_string
from accountManagementApp.models import UserProfile
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from .models import FriendRequest, Crew, CrewMember, CrewRequest, GoWithRequest
from django.db.models import Q, F
from .forms import createCrewForm
from authenticationApp.models import CustomUser
from eventManagementApp.models import SharedEvent

# Decorators to check user roles and permissions
from wave_v1.decorators import check_suspension, member, verified, onboarded

UserModel = get_user_model()


@login_required
@check_suspension
@member
@verified
def socialHomeView(request):
    user = get_object_or_404(UserProfile, user=request.user)
    siteUrl = settings.SITE_URL
    link = reverse("social:publicProfile", kwargs={"username": user.user.username})

    profileLink = f"{siteUrl}{link}"

    # Handle POST requests for friend request actions
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "acceptRequest":
            friend_request_id = request.POST.get("friend_request_id")
            friend_request = FriendRequest.objects.get(
                requestId=friend_request_id, receiver=request.user
            )
            sender = get_object_or_404(UserProfile, user=friend_request.sender)
            # We have to get the sender's user model to match the user id for the channel group name, because the channel rely's on the traditional auth user model instead of the custom user model
            senderUserModel = get_object_or_404(
                UserModel, username=sender.user.username
            )
            user.friends.add(sender)
            sender.friends.add(user)
            friend_request.accept_request()
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{senderUserModel.id}",
                {
                    "type": "friend_request_action",
                    "data": {
                        "message": "Request has been accepted.",
                    },
                },
            )
            return redirect("social:home")

        elif action == "declineRequest":
            friend_request_id = request.POST.get("friend_request_id")
            friend_request = FriendRequest.objects.get(
                requestId=friend_request_id, receiver=request.user
            )
            sender = get_object_or_404(UserProfile, user=friend_request.sender)
            # We have to get the sender's user model to match the user id for the channel group name, because the channel relies on the traditional auth user model instead of the custom user model
            senderUserModel = get_object_or_404(
                UserModel, username=sender.user.username
            )
            user.friends.remove(sender)
            sender.friends.remove(user)
            friend_request.delete()
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{senderUserModel.id}",
                {
                    "type": "friend_request_action",
                    "data": {
                        "message": "Request has been declined.",
                    },
                },
            )
            return redirect("social:home")

        elif action == "cancelRequest":
            request_id = request.POST.get("friend_request_id")
            if request_id:
                try:
                    friend_request = FriendRequest.objects.get(
                        requestId=request_id,
                        sender=request.user,
                        status="pending"
                    )
                    friend_request.status = "canceled"
                    friend_request.save()
                    messages.success(request, "Friend request canceled successfully.")
                    return redirect("social:home")
                except FriendRequest.DoesNotExist:
                    messages.error(request, "Friend request not found.")
                    return redirect("social:home")

        elif action == "cancelCrewInvite":
            crew_request_id = request.POST.get("request_id")
            crew_request = CrewRequest.objects.get(
                requestId=crew_request_id, sender=request.user
            )
            receiver = get_object_or_404(UserProfile, user=crew_request.receiver)
            # We have to get the receiver's user model to match the user id for the channel group name, because the channel relies on the traditional auth user model instead of the custom user model
            receiverUserModel = get_object_or_404(
                UserModel, username=receiver.user.username
            )
            crew_request.delete()
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{receiverUserModel.id}",
                {
                    "type": "crew_request_action",
                    "data": {
                        "message": "Crew invite has been canceled.",
                    },
                },
            )
            return redirect("social:home")
        
        elif action == "acceptGoWithRequest":
            go_with_request_id = request.POST.get("go_with_request_id")
            go_with_request = GoWithRequest.objects.get(requestId=go_with_request_id)
            go_with_request.accept_go_with()
            messages.success(request, "Go-With request accepted successfully.")
            return redirect("social:home")

        elif action == "declineGoWithRequest":
            go_with_request_id = request.POST.get("go_with_request_id")
            go_with_request = GoWithRequest.objects.get(requestId=go_with_request_id)
            go_with_request.decline_go_with()
            messages.success(request, "Go-With request declined successfully.")
            return redirect("social:home")

        elif action == "generateProfileQRCode":
            profile = UserProfile.objects.get(user=request.user)
            profile.generate_qr_code()
            profile.save()
            messages.success(request, "QR code generated successfully!")
            return redirect("social:home")

        else:
            crew_invite_action(request, request.POST.get("crew_id"), action)

    myCrews = Crew.objects.filter(created_by=request.user)
    crewsImIn = Crew.objects.filter(crew_members__user=request.user).exclude(
        created_by=request.user
    )

    def get_random_members(crew):
        crew_members = list(crew.members.all())  # Assuming `members` is a related field
        return random.sample(crew_members, min(3, len(crew_members)))

    myCrews_with_members = [
        {
            "crew": crew,
            "random_members": get_random_members(crew),
            "joined_at": (
                crew.crew_members.filter(user=request.user).first().joined_at
                if crew.crew_members.filter(user=request.user).exists()
                else None
            ),
        }
        for crew in myCrews
    ]

    crewsImIn_with_members = [
        {"crew": crew, "random_members": get_random_members(crew)} for crew in crewsImIn
    ]

    allCrews = Crew.objects.filter(crew_members__user=request.user)

    time = datetime.now().timestamp()
    friends = user.friends.all()

    my_shared_events = SharedEvent.objects.filter(sender=user).select_related(
        "event", "receiver", "crew"
    )
    shared_with_me = SharedEvent.objects.filter(receiver=user).select_related(
        "event", "sender", "crew"
    )

    if user.user.groups.filter(name="Host").exists():
        isHost = True
    else:
        isHost = False

    if (
        user.user.groups.filter(name="Onboarded").exists()
        and user.user.groups.filter(name="Verified").exists()
    ):
        isActiveUser = True
    else:
        isActiveUser = False

    pending_friend_requests = FriendRequest.objects.filter(
        receiver=request.user, status="pending"
    )
    sent_friend_requests = FriendRequest.objects.filter(
        sender=request.user, status="pending"
    )

    pending_crew_requests = CrewRequest.objects.filter(
        receiver=request.user, status="pending"
    )
    sent_crew_requests = CrewRequest.objects.filter(
        sender=request.user, status="pending"
    )

    def get_pending_crew_request_random_members(crew_request):
        crew = crew_request.crew  # Access the related Crew object from the CrewRequest
        crew_members = list(
            crew.crew_members.all()
        )  # Assuming `crew_members` is a related field
        return random.sample(crew_members, min(3, len(crew_members)))

    pendingCrewRequestsWithMembers = [
        {
            "crew": crew_request.crew,
            "sender": crew_request.sender,
            "receiver": crew_request.receiver,
            "created_at": crew_request.created_at,
            "random_members": get_pending_crew_request_random_members(crew_request),
        }
        for crew_request in pending_crew_requests
    ]

    go_with_requests_received = GoWithRequest.objects.filter(receiver=user)
    go_with_requests_sent = GoWithRequest.objects.filter(sender=user)

    return render(
        request,
        "socialApp/socialHome.html",
        {
            "pending_friend_requests": pending_friend_requests,
            "sent_friend_requests": sent_friend_requests,
            "user_profile": user,
            "pending_crew_requests": pendingCrewRequestsWithMembers,
            "sent_crew_requests": sent_crew_requests,
            "friends": friends,
            "myCrews": myCrews_with_members,
            "crewsImIn": crewsImIn_with_members,
            "time": time,
            "go_with_requests_received": go_with_requests_received,
            "go_with_requests_sent": go_with_requests_sent,
            "isHost": isHost,
            "isActiveUser": isActiveUser,
            "my_shared_events": my_shared_events,
            "shared_with_me": shared_with_me,
            "profileLink": profileLink,  
        },
    )


def copyLinkSuccessView(request):
    messages.success(request, "Profile link copied to clipboard!")

    return JsonResponse({"message": "Profile link copied to clipboard!"})


def crew_invite_action(request, crew_id, action):
    crew = get_object_or_404(Crew, crewId=crew_id)
    crew_request = get_object_or_404(CrewRequest, crew=crew, receiver=request.user)
    sender = get_object_or_404(UserProfile, user=crew_request.sender)
    receiver = get_object_or_404(UserProfile, user=request.user)

    if action == "joinCrew":
        crew_request.accept_request()
        CrewMember.objects.create(user=request.user, crew=crew)
        messages.success(request, f"You joined the {crew.name} crew.")
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{sender.user.id}",
            {
                "type": "crew_request_update",
                "data": {
                    "message": f"{request.user.username} sent you a friend request!",
                    "action": "send",
                },
            },
        )
        async_to_sync(channel_layer.group_send)(
            f"user_{receiver.user.id}",
            {
                "type": "social_update",
                "data": {
                    "message": f"{request.user.username} sent you a crew invite.",
                    "action": "acceptCrewRequest",
                },
            },
        )
        return redirect("social:crew", crewId=crew_id)

    elif action == "declineCrew":
        crew_request.decline_request()
        print(crew_request)
        crew_request.delete()
        crew_request = None
        messages.success(request, f"Crew Invite Declined")
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{sender.user.id}",
            {
                "type": "crew_request_update",
                "data": {
                    "message": f"{request.user.username} sent you a friend request!",
                    "action": "send",
                },
            },
        )
        async_to_sync(channel_layer.group_send)(
            f"user_{receiver.user.id}",
            {
                "type": "social_update",
                "data": {
                    "message": f"{request.user.username} sent you a crew invite.",
                    "action": "declineCrewRequest",
                },
            },
        )

    return redirect("social:home")


@login_required
@check_suspension
@member
@verified
def publicProfileView(request, username):
    try:
        other_user = get_object_or_404(UserModel, username=username)
        other_user_profile, created = UserProfile.objects.get_or_create(user=other_user)

        friend_request = FriendRequest.objects.filter(
            (Q(sender=request.user) & Q(receiver=other_user))
            | (Q(sender=other_user) & Q(receiver=request.user))
        ).first()

        friend_request_status = None
        if friend_request:
            friend_request_status = friend_request.status

        is_profile = request.user == other_user

        receiver = get_object_or_404(UserProfile, user__username=request.user.username)
        if request.method == "POST":
            action = request.POST.get("action")
            if action == "send_request":
                success, message, friend_request = send_friend_request(
                    request.user, other_user_profile.user.username
                )

                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"user_{other_user_profile.user.id}",
                    {
                        "type": "social_update",
                        "data": {
                            "message": f"{request.user.username} sent you a friend request!",
                            "action": "send",
                            "friend_request": {
                                "requestId": str(friend_request.requestId),
                                "sender_first_name": friend_request.sender.first_name,
                                "sender_last_name": friend_request.sender.last_name,
                                "created_at": friend_request.created_at.strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                "profile_picture": friend_request.sender.user_profile.profile_photo.url,
                            },
                        },
                    },
                )

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
                # Update the status to canceled instead of deleting
                friend_request.status = "canceled"
                friend_request.save()

                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"user_{other_user_profile.user.id}",
                    {
                        "type": "social_update",
                        "data": {
                            "message": f"{request.user.username} canceled the friend request.",
                            "action": "cancel",
                            "friend_request": {
                                "requestId": str(friend_request.requestId),
                                "sender_first_name": friend_request.sender.first_name,
                                "sender_last_name": friend_request.sender.last_name,
                                "created_at": friend_request.created_at.strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                            },
                        },
                    },
                )
                messages.success(request, "Friend request canceled.")
                friend_request_status = None
                return redirect("social:publicProfile", username=username)

            elif (
                action == "remove_request"
                and friend_request
                and friend_request_status == "accepted"
            ):
                other_user_profile.friends.remove(receiver)
                receiver.friends.remove(other_user_profile)
                friend_request_status = None
                friend_request.delete()

                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"user_{other_user_profile.user.id}",
                    {
                        "type": "social_update",
                        "data": {
                            "message": f"{request.user.username} removed you as a friend.",
                            "action": "remove",
                        },
                    },
                )
                messages.success(request, "Friend removed.")
                return redirect("social:publicProfile", username=username)

    except Http404:
        print("User not found")
        # print("User not found")
        # print("User not found")
        # print("User not found")
        # print("User not found")
        return render(request, "extras/invalid/invalid.html")

    return render(
        request,
        "socialApp/publicProfile.html",
        {
            "user": other_user,
            "user_profile": other_user_profile,
            "is_profile": is_profile,
            "friend_request_status": friend_request_status,
        },
    )


# Helper function to send friend request, decorator will make this not work because it is not a view
def send_friend_request(sender, receiver_username):
    try:
        receiver = get_object_or_404(UserProfile, user__username=receiver_username)
        
        # Check if they are already friends
        if sender.user_profile.is_friends_with(receiver.user):
            return False, "You are already friends with this user.", None
        
        # First check for any active (pending/accepted) requests
        active_request = FriendRequest.objects.filter(
            Q(sender=sender, receiver=receiver.user) | 
            Q(sender=receiver.user, receiver=sender),
            status__in=['pending', 'accepted']
        ).first()
        
        if active_request:
            if active_request.status == 'pending':
                if active_request.sender == sender:
                    return False, "You have already sent a friend request to this user.", active_request
                else:
                    return False, "This user has already sent you a friend request.", active_request
            else:  # status is 'accepted'
                return False, "You are already friends with this user.", active_request
        
        # If no active request exists, check for canceled/declined requests to reuse
        old_request = FriendRequest.objects.filter(
            sender=sender,
            receiver=receiver.user,
            status__in=['canceled', 'declined']
        ).first()
        
        if old_request:
            # Reuse the old request
            old_request.status = 'pending'
            old_request.save()
            return True, "Friend request sent successfully.", old_request
        
        # Create new friend request if none exists
        friend_request = FriendRequest.objects.create(
            sender=sender,
            receiver=receiver.user,
            status="pending"
        )
        
        return True, "Friend request sent successfully.", friend_request
    except Exception as e:
        print(f"Error in send_friend_request: {str(e)}")
        raise  # Re-raise the exception to be caught by the view


@login_required
@check_suspension
@member
@verified
def send_friend_request_view(request):
    try:
        if request.method != 'POST':
            return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)
        
        receiver_username = request.POST.get('receiver_username')
        if not receiver_username:
            return JsonResponse({'status': 'error', 'message': 'Receiver username is required'}, status=400)
        
        # Check if trying to send request to self
        if receiver_username == request.user.username:
            return JsonResponse({'status': 'error', 'message': 'You cannot send a friend request to yourself'}, status=400)
        
        try:
            success, message, friend_request = send_friend_request(request.user, receiver_username)
            
            return JsonResponse({
                'status': 'success' if success else 'error',
                'message': message
            })
        except UserProfile.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'User not found'
            }, status=404)
        except FriendRequest.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Friend request not found'
            }, status=404)
        
    except Exception as e:
        error_message = str(e)
        print(f"Error in send_friend_request_view: {error_message}")
        return JsonResponse({
            'status': 'error',
            'message': f'An error occurred: {error_message}'
        }, status=500)


@login_required
@check_suspension
@member
@verified
def cancel_friend_request(request):
    try:
        if request.method != 'POST':
            return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)
        
        receiver_username = request.POST.get('receiver_username')
        if not receiver_username:
            return JsonResponse({'status': 'error', 'message': 'Receiver username is required'}, status=400)
        
        # Find the pending friend request
        try:
            friend_request = FriendRequest.objects.get(
                sender=request.user,
                receiver__username=receiver_username,
                status='pending'
            )
            
            # Update the status to canceled
            friend_request.status = 'canceled'
            friend_request.save()
            
            # Send notification through WebSocket if needed
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"user_{friend_request.receiver.id}",
                    {
                        "type": "friend_request_action",
                        "data": {
                            "message": "Friend request has been canceled.",
                            "action": "cancel",
                            "requestId": str(friend_request.requestId)
                        },
                    },
                )
            except Exception as e:
                print(f"WebSocket notification failed: {str(e)}")
                # Continue even if WebSocket fails
            
            return JsonResponse({
                'status': 'success',
                'message': 'Friend request canceled successfully'
            })
            
        except FriendRequest.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'No pending friend request found'
            }, status=404)
            
    except Exception as e:
        print(f"Error in cancel_friend_request: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=500)


@login_required
@check_suspension
@member
@verified
def createCrewView(request):
    if request.method == "POST":
        crewForm = createCrewForm(request.POST)

        if crewForm.is_valid():
            crew_instance = crewForm.save(commit=False)
            crew_instance.created_by = request.user
            crew_instance.save()

            CrewMember.objects.create(
                user=request.user,
                crew=crew_instance,
                is_admin=True,
            )

            return redirect("social:home")

    else:
        crewForm = createCrewForm()

    return render(request, "socialApp/crews/createCrew.html", {"crewForm": crewForm})


@login_required
@check_suspension
@member
@verified
def crewView(request, crewId):
    time = datetime.now().timestamp()
    user = get_object_or_404(UserProfile, user=request.user)
    crew = get_object_or_404(Crew, crewId=crewId)

    friends = user.friends.all()
    crew_members = CrewMember.objects.filter(crew=crew)
    is_in_crew = False
    try:
        crew_member = CrewMember.objects.get(crew=crew, user=request.user)
        is_in_crew = True
    except CrewMember.DoesNotExist:
        is_in_crew = False
    friends_not_in_crew = friends.exclude(
        user__in=crew_members.values_list("user", flat=True)
    )
    pending_friends = [
        friend
        for friend in friends_not_in_crew
        if friend.has_pending_crew_request(request.user)
    ]
    declined_friends = [
        friend
        for friend in friends_not_in_crew
        if friend.has_declined_crew_request(request.user)
    ]
    not_invited_friends = friends_not_in_crew.exclude(
        user__username__in=pending_friends
    ).exclude(user__username__in=declined_friends)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "crew_invite":
            inviteeUsername = request.POST.get("invitee_username")
            receiver = get_object_or_404(UserProfile, user__username=inviteeUsername)
            success, message, crew_request = send_crew_request(
                user, inviteeUsername, crewId
            )
            if success:
                messages.success(request, message)
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"user_{receiver.user.id}",
                    {
                        "type": "social_update",
                        "data": {
                            "message": f"{request.user.username} sent you a crew invite.",
                            "action": "sendCrew",
                            "crew_request": {
                                "requestId": str(crew_request.requestId),
                                "crew": str(crew.name),
                                "crewId": str(crew.crewId),
                                "sender": {
                                    "username": str(user.user.username),
                                },
                                "profile_picture": user.profile_photo.url,
                            },
                        },
                    },
                )
            else:
                messages.warning(request, message)
            return redirect("social:crew", crewId=crewId)

        elif action == "leave_crew":
            leave_crew(request, crewId)
            crew_request = get_object_or_404(
                CrewRequest, crew=crew, receiver=request.user
            )
            sender = get_object_or_404(UserProfile, user=crew_request.sender)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{sender.user.id}",
                {
                    "type": "crew_request_update",
                    "data": {
                        "message": f"{request.user.username} left the crew.",
                        "action": "leaveCrew",
                    },
                },
            )
            return redirect("social:home")

        elif action == "delete_crew":
            delete_crew(request, crewId)
            return redirect("social:home")

        elif action == "kick_member":
            member_username = request.POST.get("member")
            kick_member(request, crewId, member_username)
            receiver = get_object_or_404(UserProfile, user__username=member_username)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{receiver.user.id}",
                {
                    "type": "social_update",
                    "data": {
                        "message": f"{request.user.username} kicked you from the crew.",
                        "action": "kickCrew",
                        "crew_request": {
                            "crew": str(crew.name),
                            "crewId": str(crew.crewId),
                            "sender": {
                                "username": str(user.user.username),
                            },
                        },
                    },
                },
            )
            return redirect("social:crew", crewId=crewId)

    return render(
        request,
        "socialApp/crews/crew.html",
        {
            "crew": crew,
            "self": user.user,
            "crewMembers": crew_members,
            "pendingFriends": pending_friends,
            "declinedFriends": declined_friends,
            "notInvitedFriends": not_invited_friends,
            "time": time,
            "isCrewOwner": crew.created_by == request.user,
            "isInCrew": is_in_crew,
        },
    )


# Helper function to send friend request, decorator will make this not work because it is not a view
def send_crew_request(sender, receiver_username, crew_id):
    sender = get_object_or_404(UserProfile, user__username=sender.user.username)
    receiver = get_object_or_404(UserProfile, user__username=receiver_username)
    crew = get_object_or_404(Crew, crewId=crew_id)

    if CrewMember.objects.filter(crew=crew, user=receiver.user).exists():
        return False, "User is already a member of the crew.", None

    crew_request, created = CrewRequest.objects.get_or_create(
        sender=sender.user,
        receiver=receiver.user,
        crew=crew,
        defaults={"status": "pending"},
    )

    if not created:
        return False, "Crew request has already been sent.", None

    return True, "Crew request sent successfully.", crew_request


@login_required
@check_suspension
@member
@verified
def leave_crew(request, crewId):
    crew = get_object_or_404(Crew, crewId=crewId)
    crew_member = CrewMember.objects.get(crew=crew, user=request.user)
    crew_member.delete()

    CrewRequest.objects.filter(crew=crew, receiver=crew_member.user).delete()
    CrewRequest.objects.filter(crew=crew, sender=crew_member.user).delete()

    crew_members = CrewMember.objects.filter(crew=crew)
    if not crew_members.exists():
        crew.delete()
        messages.success(request, f"{crew.name} crew has been deleted.")
    messages.success(request, f"{request.user} has left the {crew.name} crew.")
    return redirect("social:home")


@login_required
@check_suspension
@member
@verified
def delete_crew(request, crewId):
    crew = get_object_or_404(Crew, crewId=crewId)

    CrewRequest.objects.filter(crew=crew).delete()
    CrewMember.objects.filter(crew=crew).delete()

    crew.delete()
    messages.success(request, f"{crew.name} crew has been deleted.")
    return redirect("social:home")


@login_required
@check_suspension
@member
@verified
def kick_member(request, crewId, member_username):
    crew = get_object_or_404(Crew, crewId=crewId)
    member = get_object_or_404(UserProfile, user__username=member_username)

    CrewRequest.objects.filter(crew=crew, receiver=member.user).delete()
    CrewRequest.objects.filter(crew=crew, sender=member.user).delete()

    CrewMember.objects.filter(crew=crew, user=member.user).delete()
    messages.success(
        request, f"{member.user.username} has been kicked from the {crew.name} crew."
    )
    return redirect("social:crew", crewId=crewId)

    # if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
    #     query = request.GET.get('query', '')

    #     user_friends = user.friends.all()

    #     # Filter friends based on the search query (e.g., name)
    #     results = user_friends.filter(
    #         Q(user__username__icontains=query) |
    #         Q(user__first_name__icontains=query) |
    #         Q(user__last_name__icontains=query)
    #     )

    #     # Render each result using the template
    #     if results.exists():
    #         results_html = []
    #         for friend in results:
    #             html = render_to_string('socialApp/extras/search-item.html', {'friend': friend, "time": time, "crew": crew}, request=request)
    #             results_html.append(html)
    #         return JsonResponse({'results_html': results_html, 'no_results': False})
    #     else:
    #         no_results_html = render_to_string('socialApp/extras/no-result.html')
    #         return JsonResponse({'results_html': [], 'no_results': True, 'no_results_html': no_results_html})


def send_social_socket_message(shared_event, receiver, message, action):
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{receiver.user.id}",
            {
                "type": "social_update",
                "data": {
                    "message": message,
                    "action": action,
                    "shared_event": {
                        "event": shared_event.event.name,
                        "event_id": shared_event.event.eventId,
                        "header_photo": shared_event.event.header_photo.url,
                        "date": shared_event.event.date,
                        "sender": {
                            "username": shared_event.sender.user.username,
                        },
                        "crew": {
                            "name": shared_event.crew.name,
                            "crew_id": shared_event.crew.crewId,
                        },
                    },
                },
            },
        )
    except Exception as e:
        print(e)
        return False
    return True
