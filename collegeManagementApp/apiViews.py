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
from .serializers import CollegeSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def college_campuses_api(request):
    colleges = College.objects.all()
    serializer = CollegeSerializer(colleges, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

