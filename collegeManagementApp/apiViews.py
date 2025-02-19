from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.db.models import Q
from django.utils.timezone import now
from datetime import timedelta, date
from django.db.models import Count
from .models import  Organization, Membership
from eventManagementApp.models import Event
from adminDashboardApp.models import College
from accountManagementApp.models import UserProfile
from .serializers import CollegeSerializer, EventSerializer
from accountManagementApp.serializers import UserProfileSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def college_campuses_api(request):
    colleges = College.objects.all()
    serializer = CollegeSerializer(colleges, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def view_college_information_api(request, collegeId):
    college = get_object_or_404(College, collegeId=collegeId)
    
    user_profile = UserProfile.objects.filter(user=request.user).first() if request.user.is_authenticated else None
    is_member = Membership.objects.filter(user=request.user, college=college).exists() if request.user.is_authenticated else False
    
    members = UserProfile.objects.filter(college=college)
    organizations = Organization.objects.filter(college=college, status="Accepted")
    
    # Age restriction filtering
    if request.user.is_authenticated:
        user_age = request.user.age if hasattr(request.user, 'age') else None
        if user_age is None and hasattr(request.user, 'birthday') and request.user.birthday:
            today = date.today()
            user_age = today.year - request.user.birthday.year - ((today.month, today.day) < (request.user.birthday.month, request.user.birthday.day))
            request.user.age = user_age
            request.user.save()
    else:
        user_age = None
    
    age_filter = Q(age_restriction="")
    if user_age:
        if user_age >= 21:
            age_filter |= Q(age_restriction="21+")
        if user_age >= 18:
            age_filter |= Q(age_restriction="18+")
    
    events_restricted_to_college = Event.objects.filter(
        privacy="Private (College)",
        privacy_details__restricted_college=college,
        status="live"
    ).filter(age_filter).order_by("-date")
    
    display_events_on_college = Event.objects.filter(
        display_event_on_college=True,
        host__user_profile__college=college,
        status="live"
    ).filter(age_filter).order_by("-date")
    
    events = (events_restricted_to_college | display_events_on_college).distinct()
    
    # Weekly events
    today = now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    weekly_events = Event.objects.filter(
        date__range=[start_of_week, end_of_week],
        status="live",
        privacy="Discoverable",
        admin_status="active"
    ).filter(age_filter).order_by("?")[:3]
    
    response_data = {
        "college": CollegeSerializer(college).data,
        "college_members": UserProfileSerializer(members, many=True).data,
        "user_profile": user_profile.id if user_profile else None,
        "organizations": [org.orgId for org in organizations],
        "events":EventSerializer(events, many=True).data,
        "weekly_events": EventSerializer(weekly_events, many=True).data,
        "is_member": is_member,
    }
    
    return Response(response_data, status=status.HTTP_200_OK)