from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from django.http import JsonResponse
from django.db.models import Count
from django.shortcuts import get_object_or_404
from .models import College, Organization
from accountManagementApp.models import UserProfile


@api_view(['GET'])
@permission_classes([AllowAny])
def collegeCampusesView(request):
    """
    API endpoint for retrieving college data, including:
    - All available colleges
    - College member counts
    - College organization counts
    """

    # Handle search query
    query = request.GET.get("query", "")
    colleges = College.objects.filter(name__icontains=query) if query else College.objects.all()

    # Fetch member and organization counts efficiently
    college_data = [
        {
            "id": college.collegeId,
            "name": college.name,
            "address": college.address,
            "city": college.city,
            "state": college.state,
            "zip_code": college.zip_code,
            "country": college.country,
            "logo": college.logo.url if college.logo else None,
            "email_domain": college.email_domain,
            "motto": college.motto,
            "managers": college.managers.values("username", "first_name", "last_name"),
            "contact_website": college.contact_website,
            "member_count": UserProfile.objects.filter(college=college).count(),
            "organization_count": Organization.objects.filter(college=college).count(),
        }
        for college in colleges
    ]

    # Prepare response
    response_data = {
        "colleges": college_data,
        "total_colleges": colleges.count(),
        "no_results": not colleges.exists()
    }

    return JsonResponse(response_data, safe=False)