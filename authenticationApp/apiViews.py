from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login, logout
from adminDashboardApp.models import LoginHistoryModel
from authenticationApp.models import CustomUser
from authenticationApp.forms import UserAuthenticationForm
from authenticationApp.serializers import LoginSerializer
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils.decorators import method_decorator

from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.http import JsonResponse

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError

@api_view(['POST'])
@permission_classes([AllowAny])
def login_api(request):
    try:
        identifier = request.data.get('identifier')
        password = request.data.get('password')

        if not identifier or not password:
            return Response(
                {'error': 'Please provide both identifier and password'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if the identifier is an email or username
        user = (
            CustomUser.objects.filter(email=identifier).first()
            or CustomUser.objects.filter(username=identifier).first()
        )

        if not user:
            return Response(
                {'error': 'Invalid email/username or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Authenticate using email
        authenticated_user = authenticate(
            request,
            email=user.email,
            password=password
        )

        if not authenticated_user:
            return Response(
                {'error': 'Invalid email/username or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Create login history
        LoginHistoryModel.objects.create(
            user=authenticated_user,
            email=authenticated_user.email,
            ip_address=request.META.get('REMOTE_ADDR')
        )

        # Generate tokens
        refresh = RefreshToken.for_user(authenticated_user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': authenticated_user.id,
                'email': authenticated_user.email,
                'username': authenticated_user.username,
                # Add any other user fields you need
            }
        }, status=status.HTTP_200_OK)

    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': 'An unexpected error occurred'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({'detail': 'CSRF cookie set'})


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Update the latest login history record
            login_history = LoginHistoryModel.objects.filter(
                user=request.user
            ).latest("login_time")
            login_history.end_session()
            
            # Perform logout
            logout(request)
            
            return Response(
                {"detail": "Successfully logged out"},
                status=status.HTTP_200_OK
            )
            
        except LoginHistoryModel.DoesNotExist:
            # If no login history exists, just perform logout
            logout(request)
            return Response(
                {"detail": "Successfully logged out"},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {"error": "An error occurred during logout"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )