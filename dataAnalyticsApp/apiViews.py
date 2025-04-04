from datetime import datetime, timedelta
import time
import json
import stripe
from django import forms
from django.conf import settings
from rest_framework.views import APIView
from django.urls import reverse
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime
import uuid
from django.db.models import Q
from django.db.models import Count

from django.contrib.auth.models import User
from eventManagementApp.models import Event



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_event_analytics(request, eventId):
    try:
        eventAnalyticsUrl = reverse(
            "eventManagement:hostEventAnalytics", kwargs={"eventId": eventId}
        )
        
        eventAnalyticsUrl = request.build_absolute_uri(eventAnalyticsUrl)
        
        return Response(
            {
                "url": eventAnalyticsUrl,
                "status": "success"
            }, 
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {
                "error": str(e),
                "status": "failed"
            }, 
            status=status.HTTP_400_BAD_REQUEST
        )