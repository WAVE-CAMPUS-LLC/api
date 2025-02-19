from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.urls import reverse
from datetime import datetime
import random
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import FriendRequest, Crew, CrewMember, CrewRequest
from accountManagementApp.models import UserProfile
from authenticationApp.models import CustomUser
from eventManagementApp.models import SharedEvent
from accountManagementApp.serializers import UserProfileSerializer
from eventManagementApp.serializers import SharedEventSerializer
from .serializers import CrewSerializer, FriendRequestSerializer, CrewRequestSerializer

from wave_v1.decorators import check_suspension, member, verified



class SocialHomeView(APIView):
    permission_classes = [IsAuthenticated]

    @check_suspension
    @member
    @verified
    def get(self, request):
        user = get_object_or_404(UserProfile, user=request.user)
        site_url = settings.SITE_URL
        profile_link = f"{site_url}{reverse('social:publicProfile', kwargs={'username': user.user.username})}"

        my_crews = Crew.objects.filter(created_by=request.user)
        crews_im_in = Crew.objects.filter(crew_members__user=request.user).exclude(created_by=request.user)

        def get_random_members(crew):
            crew_members = list(crew.members.all())
            return random.sample(crew_members, min(3, len(crew_members)))

        my_crews_with_members = [
            {
                "crew": CrewSerializer(crew).data,
                "random_members": UserProfileSerializer(get_random_members(crew), many=True).data,
                "joined_at": crew.crew_members.filter(user=request.user).first().joined_at if crew.crew_members.filter(user=request.user).exists() else None,
            }
            for crew in my_crews
        ]

        crews_im_in_with_members = [
            {
                "crew": CrewSerializer(crew).data,
                "random_members": UserProfileSerializer(get_random_members(crew), many=True).data
            }
            for crew in crews_im_in
        ]

        friends = UserProfileSerializer(user.friends.all(), many=True).data
        my_shared_events = SharedEventSerializer(SharedEvent.objects.filter(sender=user), many=True).data
        shared_with_me = SharedEventSerializer(SharedEvent.objects.filter(receiver=user), many=True).data

        is_host = user.user.groups.filter(name="Host").exists()
        is_active_user = user.user.groups.filter(name="Onboarded").exists() and user.user.groups.filter(name="Verified").exists()

        pending_friend_requests = FriendRequestSerializer(
            FriendRequest.objects.filter(receiver=request.user, status="pending"), many=True
        ).data
        sent_friend_requests = FriendRequestSerializer(
            FriendRequest.objects.filter(sender=request.user, status="pending"), many=True
        ).data

        pending_crew_requests = CrewRequest.objects.filter(receiver=request.user, status="pending")
        sent_crew_requests = CrewRequestSerializer(
            CrewRequest.objects.filter(sender=request.user, status="pending"), many=True
        ).data

        def get_pending_crew_request_random_members(crew_request):
            crew = crew_request.crew
            crew_members = list(crew.crew_members.all())
            return random.sample(crew_members, min(3, len(crew_members)))

        pending_crew_requests_with_members = [
            {
                "crew": CrewSerializer(crew_request.crew).data,
                "sender": UserProfileSerializer(crew_request.sender).data,
                "receiver": UserProfileSerializer(crew_request.receiver).data,
                "created_at": crew_request.created_at,
                "random_members": UserProfileSerializer(get_pending_crew_request_random_members(crew_request), many=True).data,
            }
            for crew_request in pending_crew_requests
        ]

        return Response({
            "pending_friend_requests": pending_friend_requests,
            "sent_friend_requests": sent_friend_requests,
            "user_profile": UserProfileSerializer(user).data,
            "pending_crew_requests": pending_crew_requests_with_members,
            "sent_crew_requests": sent_crew_requests,
            "friends": friends,
            "myCrews": my_crews_with_members,
            "crewsImIn": crews_im_in_with_members,
            "time": datetime.now().timestamp(),
            "isHost": is_host,
            "isActiveUser": is_active_user,
            "my_shared_events": my_shared_events,
            "shared_with_me": shared_with_me,
            "profileLink": profile_link,
        })
