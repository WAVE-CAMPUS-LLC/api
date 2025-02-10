from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from adminDashboardApp.models import LoginHistoryModel
from authenticationApp.models import CustomUser
from authenticationApp.forms import UserAuthenticationForm
from authenticationApp.serializers import LoginSerializer
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils.decorators import method_decorator

from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.http import JsonResponse

@method_decorator(ensure_csrf_cookie, name='dispatch')
@api_view(["POST"])
@permission_classes([AllowAny])
def login_api_view(request):
    """
    API View for user login with email/username and password.
    Returns JWT tokens upon successful authentication.
    """
    identifier = request.data.get("identifier")
    password = request.data.get("password")

    if not identifier or not password:
        return Response({"error": "Email/Username and password are required."}, status=400)

    # Find user by email or username
    user = (
        CustomUser.objects.filter(email=identifier).first()
        or CustomUser.objects.filter(username=identifier).first()
    )

    if user:
        user = authenticate(request, email=user.email, password=password)  # Authenticate with email

        if user:
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Log login activity
            LoginHistoryModel.objects.create(
                user=user,
                email=user.email,
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
            })

    return Response({"error": "Invalid email/username or password"}, status=400)


@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({'detail': 'CSRF cookie set'})