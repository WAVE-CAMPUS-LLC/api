from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.db.models import Count
from .models import  Organization
from adminDashboardApp.models import College
from accountManagementApp.models import UserProfile


@api_view(['GET'])
@permission_classes([AllowAny])
def college_campuses_api(request):
    query = request.GET.get("query", "")

    if query:
        results = College.objects.filter(name__icontains=query)
        if results.exists():
            results_html = [
                render_to_string("collegeManagementApp/extras/search-item.html", {"college": college})
                for college in results
            ]
            return Response({"results_html": results_html, "no_results": False}, status=status.HTTP_200_OK)
        else:
            no_results_html = render_to_string("collegeManagementApp/extras/no-result.html")
            return Response({"results_html": [], "no_results": True, "no_results_html": no_results_html}, status=status.HTTP_200_OK)

    colleges = College.objects.all()
    college_members_info = [
        {
            "college_name": college.name,
            "member_count": UserProfile.objects.filter(college=college).count(),
            "organization_count": Organization.objects.filter(college=college).count(),
        }
        for college in colleges
    ]

    user_profile = None
    if request.user.is_authenticated:
        user_profile = UserProfile.objects.filter(user=request.user).first()
        user_profile_data = {"id": user_profile.id, "college": user_profile.college.name} if user_profile else None
    else:
        user_profile_data = None

    return Response({
        "pageName": "Colleges",
        "college_members_info": college_members_info,
        "user_profile": user_profile_data
    }, status=status.HTTP_200_OK)

