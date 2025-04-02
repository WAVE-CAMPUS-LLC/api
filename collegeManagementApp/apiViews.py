from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.crypto import get_random_string
from django.contrib import messages

from django.template.loader import render_to_string
from django.http import JsonResponse
from django.db.models import Q
from django.utils.timezone import now
from datetime import timedelta, date
from django.db.models import Count

from .models import Organization, Membership
from .forms import JoinCollegeForm, VerifyCollegeJoinForm

from eventManagementApp.models import Event
from adminDashboardApp.models import College
from accountManagementApp.models import UserProfile
from .serializers import CollegeSerializer, EventSerializer, OrganizationSerializer
from accountManagementApp.serializers import UserProfileSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def college_campuses_api(request):
    colleges = College.objects.all()
    serializer = CollegeSerializer(colleges, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def view_college_information_api(request, collegeId):
    college = get_object_or_404(College, collegeId=collegeId)

    user_profile = (
        UserProfile.objects.filter(user=request.user).first()
        if request.user.is_authenticated
        else None
    )
    is_member = (
        Membership.objects.filter(user=request.user, college=college).exists()
        if request.user.is_authenticated
        else False
    )

    members = UserProfile.objects.filter(college=college)
    organizations = Organization.objects.filter(college=college, status="Accepted")

    # Age restriction filtering logic

    events = Event.objects.filter(
        Q(forCollegesDisplay=True, host__user_profile__college=college)
        | Q(forAllDisplay=True, host__user_profile__college=college),
        status="live",
    ).order_by("-date")

    # Weekly events
    today = now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    weekly_events = Event.objects.filter(
        date__range=[start_of_week, end_of_week],
        status="live",
        forCollegesDisplay=True,
        admin_status="active",
    ).order_by("?")[:3]

    response_data = {
        "college": CollegeSerializer(college).data,
        "college_members": UserProfileSerializer(members, many=True).data,
        "user_profile": user_profile.id if user_profile else None,
        "organizations": OrganizationSerializer(organizations, many=True).data,
        "events": EventSerializer(events, many=True).data,
        "weekly_events": EventSerializer(weekly_events, many=True).data,
        "is_member": is_member,
    }

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def join_college_api(request, collegeId):
    college = get_object_or_404(College, collegeId=collegeId)

    joinForm = JoinCollegeForm(request.data, college=college)
    joinForm.user = request.user

    if joinForm.is_valid():
        email = joinForm.cleaned_data["email"]
        domain = email.split("@")[1]
        code = get_random_string(
            6, allowed_chars="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        )

        # Store verification data in session
        request.session["verification_code"] = code
        request.session["college_id"] = str(collegeId)
        request.session["user_email"] = email

        try:
            send_mail(
                "Verify your campus email",
                f"Your verification code is: {code}",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return Response(
                {
                    "message": "Verification email sent successfully",
                    "next_step": "verify",
                    "collegeId": collegeId,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": "Failed to send verification email", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return Response({"errors": joinForm.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST", "GET"])
@permission_classes([IsAuthenticated])
def verify_join_college_api(request, collegeId):
    """
    API endpoint for verifying college join verification code
    """
    college = get_object_or_404(College, collegeId=collegeId)
    verifyForm = VerifyCollegeJoinForm(request.data)

    if verifyForm.is_valid():
        code = verifyForm.cleaned_data["code"]
        stored_code = request.session.get("verification_code")

        if not stored_code:
            return Response(
                {
                    "error": "No verification code found in session. Please request a new code."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if code == stored_code:
            user_profile = get_object_or_404(UserProfile, user=request.user)
            user_profile.college = college
            user_profile.save()

            # Create college membership
            membership, created = Membership.objects.get_or_create(
                user=request.user, college=college
            )

            # Clear session data
            request.session.pop("verification_code", None)
            request.session.pop("college_id", None)
            request.session.pop("user_email", None)

            return Response(
                {
                    "message": f"You have successfully joined {college.name}",
                    "college": {"id": college.collegeId, "name": college.name},
                    "membership_created": created,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"error": "Invalid verification code"}, status=status.HTTP_400_BAD_REQUEST
        )

    return Response({"errors": verifyForm.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST", "GET"])
@permission_classes([IsAuthenticated])
def exit_college_api(request, collegeId):
    """
    API endpoint for leaving a college
    """
    user_profile = get_object_or_404(UserProfile, user=request.user)
    college = get_object_or_404(College, collegeId=collegeId)

    try:
        college_membership = Membership.objects.get(user=request.user, college=college)
    except Membership.DoesNotExist:
        return Response(
            {"error": "You aren't a member of this college."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if user_profile.college and str(user_profile.college.collegeId) == str(collegeId):
        # Remove college from user profile and delete membership
        user_profile.college = None
        college_membership.delete()
        user_profile.save()

        return Response(
            {
                "message": "You have successfully left the college.",
                "college": {"id": collegeId, "name": college.name},
            },
            status=status.HTTP_200_OK,
        )
