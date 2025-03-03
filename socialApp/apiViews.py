from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.urls import reverse
from datetime import datetime
import random
from django.utils.timezone import now
from rest_framework import status
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import FriendRequest, Crew, CrewMember, CrewRequest
from accountManagementApp.models import UserProfile
from authenticationApp.models import CustomUser
from eventManagementApp.models import SharedEvent
from accountManagementApp.serializers import UserProfileSerializer
from eventManagementApp.serializers import SharedEventSerializer
from .serializers import CrewSerializer, FriendRequestSerializer, CrewRequestSerializer
from authenticationApp.serializers import CustomUserSerializer
from django.contrib.auth import get_user_model
from django.db.models import Q

from wave_v1.decorators import check_suspension, member, verified



class SocialHomeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_profile = get_object_or_404(UserProfile, user=request.user)
        site_url = settings.SITE_URL
        profile_link = f"{site_url}{reverse('social:publicProfile', kwargs={'username': user_profile.user.username})}"
        
        my_crews = Crew.objects.filter(created_by=request.user)
        crews_im_in = Crew.objects.filter(crew_members__user=request.user).exclude(created_by=request.user)
        friends = user_profile.friends.all()
        my_shared_events = SharedEvent.objects.filter(sender=user_profile).select_related("event", "receiver", "crew")
        shared_with_me = SharedEvent.objects.filter(receiver=user_profile).select_related("event", "sender", "crew")
        pending_friend_requests = FriendRequest.objects.filter(receiver=request.user, status="pending")
        sent_friend_requests = FriendRequest.objects.filter(sender=request.user, status="pending")
        pending_crew_requests = CrewRequest.objects.filter(receiver=request.user, status="pending")
        sent_crew_requests = CrewRequest.objects.filter(sender=request.user, status="pending")

        is_host = user_profile.user.groups.filter(name="Host").exists()
        is_active_user = (user_profile.user.groups.filter(name="Onboarded").exists() and
                          user_profile.user.groups.filter(name="Verified").exists())
        
        response_data = {
            "user_profile": UserProfileSerializer(user_profile).data,
            "profile_link": profile_link,
            "friends": UserProfileSerializer(friends, many=True).data,
            "my_crews": CrewSerializer(my_crews, many=True).data,
            "crews_im_in": CrewSerializer(crews_im_in, many=True).data,
            "my_shared_events": SharedEventSerializer(my_shared_events, many=True).data,
            "shared_with_me": SharedEventSerializer(shared_with_me, many=True).data,
            "pending_friend_requests": FriendRequestSerializer(pending_friend_requests, many=True).data,
            "sent_friend_requests": FriendRequestSerializer(sent_friend_requests, many=True).data,
            "pending_crew_requests": CrewRequestSerializer(pending_crew_requests, many=True).data,
            "sent_crew_requests": CrewRequestSerializer(sent_crew_requests, many=True).data,
            "is_host": is_host,
            "is_active_user": is_active_user,
            "timestamp": now().timestamp(),
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request):
        action = request.data.get("action")
        friend_request_id = request.data.get("friend_request_id")
        crew_request_id = request.data.get("request_id")

        if action == "acceptRequest":
            friend_request = get_object_or_404(FriendRequest, requestId=friend_request_id, receiver=request.user)
            sender = get_object_or_404(UserProfile, user=friend_request.sender)
            sender_user_model = get_object_or_404(CustomUser, username=sender.user.username)
            user_profile = get_object_or_404(UserProfile, user=request.user)
            user_profile.friends.add(sender)
            sender.friends.add(user_profile)
            friend_request.accept_request()
            # self.send_notification(sender_user_model.id, "Request has been accepted.")
            return Response({"message": "Friend request accepted."}, status=status.HTTP_200_OK)

        elif action == "declineRequest":
            friend_request = get_object_or_404(FriendRequest, requestId=friend_request_id, receiver=request.user)
            friend_request.delete()
            return Response({"message": "Friend request declined."}, status=status.HTTP_200_OK)

        elif action == "cancelRequest":
            try:
                friend_request = FriendRequest.objects.get(requestId=friend_request_id, sender=request.user, status="pending")
                friend_request.status = "canceled"
                friend_request.save()
                return Response({"message": "Friend request canceled."}, status=status.HTTP_200_OK)
            except FriendRequest.DoesNotExist:
                return Response({"error": "Friend request not found."}, status=status.HTTP_404_NOT_FOUND)

        elif action == "cancelCrewInvite":
            crew_request = get_object_or_404(CrewRequest, requestId=crew_request_id, sender=request.user)
            receiver = get_object_or_404(UserProfile, user=crew_request.receiver)
            receiver_user_model = get_object_or_404(CustomUser, username=receiver.user.username)
            crew_request.delete()
            # self.send_notification(receiver_user_model.id, "Crew invite has been canceled.")
            return Response({"message": "Crew invite canceled."}, status=status.HTTP_200_OK)

        elif action == "generateProfileQRCode":
            profile = get_object_or_404(UserProfile, user=request.user)
            profile.generate_qr_code()
            profile.save()
            return Response({"message": "QR code generated successfully!"}, status=status.HTTP_200_OK)

        return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)


class NonFriendsListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        User = get_user_model()
        
        # Get all accepted friend requests where the current user is either sender or receiver
        accepted_friends = FriendRequest.objects.filter(
            (Q(sender=request.user) | Q(receiver=request.user)),
            status='accepted'
        )
        
        # Get the list of friend user IDs
        friend_ids = []
        for friendship in accepted_friends:
            if friendship.sender == request.user:
                friend_ids.append(friendship.receiver.id)
            else:
                friend_ids.append(friendship.sender.id)
        
        # Get all users who are not friends (excluding the request user), and who have profiles
        non_friends = User.objects.filter(
            user_profile__isnull=False  # Only include users who have profiles
        ).exclude(
            id__in=friend_ids
        ).exclude(
            id=request.user.id
        ).select_related('user_profile')
        
        # Create a list to store combined data
        combined_data = []
        for user in non_friends:
            try:
                user_data = CustomUserSerializer(user).data
                profile_data = UserProfileSerializer(user.user_profile).data
                combined_data.append({
                    'user': user_data,
                    'profile': profile_data
                })
            except User.user_profile.RelatedObjectDoesNotExist:
                # Skip users without profiles (this shouldn't happen due to our filter, but just in case)
                continue
        
        return Response(combined_data, status=status.HTTP_200_OK)


class PublicProfileAPIView(APIView):
    permission_classes = []  # Remove default permission requirements
    
    def get(self, request, username):
        """
        Get a user's public profile - accessible to anyone
        """
        try:
            # Get the requested user and their profile
            other_user = get_object_or_404(CustomUser, username=username)
            other_user_profile, created = UserProfile.objects.get_or_create(user=other_user)
            
            # Initialize friend-related data
            friend_request_status = None
            friend_request_id = None
            is_profile = False
            
            # Only check friendship status if the user is authenticated
            if request.user.is_authenticated:
                # Check if the users are friends or have pending requests
                friend_request = FriendRequest.objects.filter(
                    (Q(sender=request.user) & Q(receiver=other_user))
                    | (Q(sender=other_user) & Q(receiver=request.user))
                ).first()
                
                if friend_request:
                    friend_request_status = friend_request.status
                    friend_request_id = str(friend_request.requestId)
                
                is_profile = request.user.id == other_user.id
            
            # Prepare response data
            response_data = {
                "user": CustomUserSerializer(other_user).data,
                "user_profile": UserProfileSerializer(other_user_profile).data,
                "is_profile": is_profile,
            }
            
            # Only include friendship data for authenticated users
            if request.user.is_authenticated:
                response_data.update({
                    "friend_request_status": friend_request_status,
                    "friend_request_id": friend_request_id,
                    "can_send_request": request.user.is_authenticated
                })
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request, username):
        """
        Handle friend request actions - requires authentication
        """
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required to perform this action."},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        try:
            # Get the requested user and their profile
            other_user = get_object_or_404(CustomUser, username=username)
            other_user_profile, created = UserProfile.objects.get_or_create(user=other_user)
            
            # Get the current user's profile
            receiver = get_object_or_404(UserProfile, user=request.user)
            
            # Get any existing friend request
            friend_request = FriendRequest.objects.filter(
                (Q(sender=request.user) & Q(receiver=other_user))
                | (Q(sender=other_user) & Q(receiver=request.user))
            ).first()
            
            action = request.data.get("action")
            
            if action == "send_request":
                # Logic moved from send_friend_request method directly into this action handler
                try:
                    # Check if they are already friends
                    if hasattr(request.user, 'user_profile') and request.user.user_profile.is_friends_with(other_user):
                        return Response({"message": "You are already friends with this user."}, status=status.HTTP_400_BAD_REQUEST)
                    
                    # First check for any active (pending/accepted) requests
                    active_request = FriendRequest.objects.filter(
                        Q(sender=request.user, receiver=other_user) | 
                        Q(sender=other_user, receiver=request.user),
                        status__in=['pending', 'accepted']
                    ).first()
                    
                    if active_request:
                        if active_request.status == 'pending':
                            if active_request.sender == request.user:
                                return Response({"message": "You have already sent a friend request to this user."}, status=status.HTTP_400_BAD_REQUEST)
                            else:
                                return Response({"message": "This user has already sent you a friend request."}, status=status.HTTP_400_BAD_REQUEST)
                        else:  # status is 'accepted'
                            return Response({"message": "You are already friends with this user."}, status=status.HTTP_400_BAD_REQUEST)
                    
                    # If no active request exists, check for canceled/declined requests to reuse
                    old_request = FriendRequest.objects.filter(
                        sender=request.user,
                        receiver=other_user,
                        status__in=['canceled', 'declined']
                    ).first()
                    
                    if old_request:
                        # Reuse the old request
                        old_request.status = 'pending'
                        old_request.save()
                        friend_request = old_request
                    else:
                        # Create new friend request if none exists
                        friend_request = FriendRequest.objects.create(
                            sender=request.user,
                            receiver=other_user,
                            status="pending"
                        )
                    
                    # Send notification via WebSocket
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f"user_{other_user.id}",
                        {
                            "type": "social_update",
                            "data": {
                                "message": f"{request.user.username} sent you a friend request!",
                                "action": "send",
                                "friend_request": {
                                    "requestId": str(friend_request.requestId),
                                    "sender_first_name": friend_request.sender.first_name,
                                    "sender_last_name": friend_request.sender.last_name,
                                    "created_at": friend_request.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                                    "profile_picture": friend_request.sender.user_profile.profile_photo.url if friend_request.sender.user_profile.profile_photo else None,
                                },
                            },
                        },
                    )
                    
                    return Response({"message": "Friend request sent successfully.", "friend_request": FriendRequestSerializer(friend_request).data}, status=status.HTTP_200_OK)
                except Exception as e:
                    print(f"Error in send_friend_request action: {str(e)}")
                    return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
                    
            elif action == "cancel_request" and friend_request and friend_request.status == "pending":
                # Update the status to canceled instead of deleting
                friend_request.status = "canceled"
                friend_request.save()
                
                # Send notification via WebSocket
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"user_{other_user.id}",
                    {
                        "type": "social_update",
                        "data": {
                            "message": f"{request.user.username} canceled the friend request.",
                            "action": "cancel",
                            "friend_request": {
                                "requestId": str(friend_request.requestId),
                                "sender_first_name": friend_request.sender.first_name,
                                "sender_last_name": friend_request.sender.last_name,
                                "created_at": friend_request.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                            },
                        },
                    },
                )
                
                return Response({"message": "Friend request canceled."}, status=status.HTTP_200_OK)
                
            elif action == "remove_request" and friend_request and friend_request.status == "accepted":
                other_user_profile.friends.remove(receiver)
                receiver.friends.remove(other_user_profile)
                friend_request.delete()
                
                # Send notification via WebSocket
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"user_{other_user.id}",
                    {
                        "type": "social_update",
                        "data": {
                            "message": f"{request.user.username} removed you as a friend.",
                            "action": "remove",
                        },
                    },
                )
                
                return Response({"message": "Friend removed."}, status=status.HTTP_200_OK)
                
            else:
                return Response({"message": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


