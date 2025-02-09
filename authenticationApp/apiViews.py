from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from adminDashboardApp.models import LoginHistoryModel
from authenticationApp.forms import UserAuthenticationForm
from authenticationApp.serializers import LoginSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):  # Rename function to avoid conflict with Django's login function
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        user = authenticate(request=request, email=email, password=password)

        if user:
            django_login(request, user)  # Use Django's login function properly

            LoginHistoryModel.objects.create(
                user=user,
                email=user.email,
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            return Response(
                {"message": "Login successful", "user_id": user.id},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"error": "Invalid email or password"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)