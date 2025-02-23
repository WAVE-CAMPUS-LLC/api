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
            self.send_notification(sender_user_model.id, "Request has been accepted.")
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
            self.send_notification(receiver_user_model.id, "Crew invite has been canceled.")
            return Response({"message": "Crew invite canceled."}, status=status.HTTP_200_OK)

        elif action == "generateProfileQRCode":
            profile = get_object_or_404(UserProfile, user=request.user)
            profile.generate_qr_code()
            profile.save()
            return Response({"message": "QR code generated successfully!"}, status=status.HTTP_200_OK)

        return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)

class NonFriendsListView(APIView):
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
        
        # Get all users who are not friends (excluding the request user)
        non_friends = User.objects.exclude(
            id__in=friend_ids
        ).exclude(
            id=request.user.id
        )
        
        serializer = CustomUserSerializer(non_friends, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


