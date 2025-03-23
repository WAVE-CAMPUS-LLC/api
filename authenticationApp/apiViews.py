from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import ValidationError
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.template.loader import get_template, render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.http import JsonResponse
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from datetime import timedelta, datetime

from .forms import (
    CustomUserJoinForm, 
    EmailPasswordResetForm, 
    NewPasswordForm, 
    UserAuthenticationForm,
    MobileCustomUserJoinForm
)
from .models import CustomUser, EmailVerification
from wave_v1.apiDecorators import include_form_fields
from adminDashboardApp.models import College, LoginHistoryModel
from stripeManagementApp.customerSetup import CustomerAccount
from campusManagerApp.models import CampusManagerInvite
from django.contrib.auth.models import Group
from django.conf import settings
from .views import generateVerificationCode
from .serializers import CustomUserSerializer

ResetLinkExpiryTime = timedelta(hours=2)

@api_view(["POST"])
@permission_classes([AllowAny])
@include_form_fields(UserAuthenticationForm)
def login_api(request):
    try:
        identifier = request.data.get("identifier")
        password = request.data.get("password")

        if not identifier or not password:
            return Response(
                {"error": "Please provide both identifier and password"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if the identifier is an email or username
        user = (
            CustomUser.objects.filter(email=identifier).first()
            or CustomUser.objects.filter(username=identifier).first()
        )

        if not user:
            return Response(
                {"error": "Invalid email/username or password"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Authenticate using email
        authenticated_user = authenticate(request, email=user.email, password=password)

        if not authenticated_user:
            return Response(
                {"error": "Invalid email/username or password"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Create login history
        LoginHistoryModel.objects.create(
            user=authenticated_user,
            email=authenticated_user.email,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        # Generate tokens
        refresh = RefreshToken.for_user(authenticated_user)

        # Serialize the user data
        user_serializer = CustomUserSerializer(authenticated_user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user_serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {"error": "An unexpected error occurred"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST", "GET"])
@permission_classes([AllowAny])
@include_form_fields(MobileCustomUserJoinForm)
def join_api(request):
    try:
        # Determine if request is from mobile
        is_mobile = request.headers.get('X-Platform') == 'mobile'
        
        # Get session data if available
        invite_token = request.session.get("invite_token")
        invite_email = request.session.get("invite_email")
        collegeId = request.session.get("collegeId")

        # Use appropriate form based on platform
        FormClass = MobileCustomUserJoinForm if is_mobile else CustomUserJoinForm
        form = FormClass(request.data)
        
        if not form.is_valid():
            return Response({"error": form.errors}, status=status.HTTP_400_BAD_REQUEST)

        # Rest of the existing join_api code...
        user = form.save()

        # Add user to all required groups
        unverified_group, _ = Group.objects.get_or_create(name="Unverified")
        member_group, _ = Group.objects.get_or_create(name="Member")
        verified_group, _ = Group.objects.get_or_create(name="Verified")
        host_group, _ = Group.objects.get_or_create(name="Host")

        # Add all groups to user
        user.groups.add(member_group)
        user.groups.add(verified_group)
        user.groups.add(host_group)

        # Create email verification
        verification_code = generateVerificationCode()
        expiration_time = timezone.now() + timedelta(hours=12)
        email_verification = EmailVerification.objects.create(
            user=user,
            verification_code=verification_code,
            expiration_date=expiration_time,
        )

        # Send verification email
        template = get_template(
            "emailManagement/build_production/emails/authenticationApp/verifyEmail.html"
        )
        emailMessage = template.render({"verification_code": verification_code})
        plainMessage = strip_tags(emailMessage)

        send_mail(
            subject="Welcome to WAVE.! Verify your email",
            message=plainMessage,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            fail_silently=False,
            html_message=emailMessage,
        )

        user = CustomUser.objects.get(email=user.email)
        user.email_verified = True  # Set email as verified
        user.save()

        # Log the user in
        login(request, user)

        response_data = {
            "message": "User registered successfully",
            "email_verification_sent": True,
        }

        # Handle campus manager invite if present
        if invite_email and collegeId and invite_token:
            try:
                college = College.objects.get(collegeId=collegeId)
                college.managers.add(user)

                invite = CampusManagerInvite.objects.get(
                    token=invite_token, email=invite_email, college=college
                )
                invite.accepted = True
                invite.save()

                # Clear session data
                del request.session["invite_email"]
                del request.session["collegeId"]
                del request.session["invite_token"]

                response_data["college_manager"] = {
                    "college_name": college.name,
                    "role": "manager",
                }

            except (College.DoesNotExist, CampusManagerInvite.DoesNotExist):
                return Response(
                    {"error": "Invalid college or invite details"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Create customer account
        if not user.customer_id:
            customer = CustomerAccount.createCustomerAccount(
                request, user.email, user.first_name, user.last_name
            )
            if (customer):
                user.customer_id = customer["id"]
                user.save()
                response_data["customer_account_created"] = True
            else:
                response_data["customer_account_created"] = False
                response_data["warning"] = "Failed to create customer account"

        # Generate tokens
        refresh = RefreshToken.for_user(user)
        response_data["tokens"] = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

        # Add user data to response
        user_serializer = CustomUserSerializer(user)
        response_data["user"] = user_serializer.data

        return Response(response_data, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({"detail": "CSRF cookie set"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_api(request):
    try:
        # Update the latest login history record
        login_history = LoginHistoryModel.objects.filter(user=request.user).latest(
            "login_time"
        )
        login_history.end_session()

        # Perform logout
        logout(request)

        return Response(
            {"detail": "Successfully logged out"}, status=status.HTTP_200_OK
        )

    except LoginHistoryModel.DoesNotExist:
        # If no login history exists, just perform logout
        logout(request)
        return Response(
            {"detail": "Successfully logged out"}, status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {"error": "An error occurred during logout"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
@include_form_fields(EmailPasswordResetForm)
def forgot_password_api(request):
    try:
        emailForm = EmailPasswordResetForm(request.data)
        if not emailForm.is_valid():
            return Response(
                {"error": emailForm.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        email = emailForm.cleaned_data["email"]
        user = CustomUser.objects.filter(email=email).first()

        if not user:
            return Response(
                {"error": "Account does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Generate password reset token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        expiry_time = timezone.now() + ResetLinkExpiryTime

        # Create reset URL
        reset_url = request.build_absolute_uri(
            reverse(
                "authentication:passwordReset",
                kwargs={"uidb64": uid, "token": token},
            )
        )
        reset_url += f"?expires={expiry_time.timestamp()}"

        # Send email
        subject = "Request to reset password | WAVE."
        message = render_to_string(
            "authenticationApp/passwordReset/email/resetEmailTemplate.html",
            {"reset_url": reset_url},
        )
        
        try:
            send_mail(subject, message, None, [email])
        except Exception as e:
            return Response(
                {"error": "Failed to send reset email"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            "message": "Password reset email sent successfully",
            "email": email,
            "expiry_time": expiry_time
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
@include_form_fields(NewPasswordForm)
def set_new_password_api(request, uidb64, token):
    try:
        # Decode user id and get user
        uid = urlsafe_base64_decode(uidb64).decode()
        user = CustomUser.objects.get(pk=uid)
        
        if not user or not default_token_generator.check_token(user, token):
            return Response(
                {"error": "Invalid password reset link"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check expiry time
        expiry_timestamp = request.GET.get("expiry")
        if expiry_timestamp:
            expiry_time = datetime.fromtimestamp(float(expiry_timestamp))
            current_time = timezone.now()

            if current_time > expiry_time:
                return Response(
                    {"error": "Password reset link has expired"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Validate new password
        form = NewPasswordForm(request.data)
        if not form.is_valid():
            return Response(
                {"error": form.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password
        password = form.cleaned_data.get("password")
        user.set_password(password)
        user.save()

        # Log user in and generate tokens
        login(request, user)
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "message": "Password reset successful",
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            },
            "user": CustomUserSerializer(user).data
        }, status=status.HTTP_200_OK)

    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist) as e:
        return Response(
            {"error": "Invalid reset link"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": "An error occurred while resetting password"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
