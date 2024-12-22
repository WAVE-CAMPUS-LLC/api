import datetime
import random
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.contrib.auth.views import PasswordResetConfirmView
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth.decorators import login_required
from .forms import (
    CustomUserJoinForm,
    UserAuthenticationForm,
    EmailPasswordResetForm,
    NewPasswordForm,
)
from django.contrib.auth import login, logout, authenticate
from .models import CustomUser, EmailVerification
from adminDashboardApp.models import College, LoginHistoryModel
from campusManagerApp.models import CampusManagerInvite
from django.contrib.auth.models import Group

from wave_v1.decorators import (
    check_suspension,
)


# Create your views here.
def generateVerificationCode():
    return str(random.randint(100000, 999999))


def joinView(request):
    invite_token = request.session.get("invite_token")
    invite_email = request.session.get("invite_email")
    collegeId = request.session.get("collegeId")

    if request.method == "POST":
        form = CustomUserJoinForm(request.POST)
        if form.is_valid():
            user = form.save()

            group, created = Group.objects.get_or_create(name="Member")
            unverified_group, created = Group.objects.get_or_create(
                name="Unverified Email"
            )
            user.groups.add(group)
            user.groups.add(unverified_group)

            verification_code = generateVerificationCode()
            expiration_time = timezone.now() + timedelta(hours=12)
            email_verification = EmailVerification.objects.create(
                user=user,
                verification_code=verification_code,
                expiration_date=expiration_time,
            )
            
            send_mail(
                subject="Your Verification Code",
                message=f"Your verification code is {verification_code}",
                from_email="no-reply@wavecampus.net",
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            user = CustomUser.objects.get(email=user.email)
            user.is_onboarded = False
            

            if invite_email and collegeId and invite_token:
                college = College.objects.get(collegeId=collegeId)
                college.managers.add(user)

                # Mark the invite as accepted
                invite = CampusManagerInvite.objects.get(
                    token=invite_token, email=invite_email, college=college
                )
                invite.accepted = True
                invite.save()

                del request.session["invite_email"]
                del request.session["collegeId"]
                del request.session["invite_token"]

                login(request, user)
                messages.success(
                    request,
                    f"You have successfully joined {college.name} as a manager!",
                )
                return redirect("campusManager:dashboard")

            messages.info(request, "A verification code has been sent to your email.")
            login(request, user)
            next_url = request.GET.get("next", "authentication:onboarding")
            return redirect(next_url)
        else:
            print(form.errors)
    else:
        form = CustomUserJoinForm()
    return render(request, "authenticationApp/join.html", {"form": form})

@login_required
def onboardingView(request):
    if request.method == "POST":
        verification_code = request.POST.get("verification_code")
        email_verification = EmailVerification.objects.filter(user=request.user, is_verified=False).first()
        user  = CustomUser.objects.get(email=request.user.email)
        if email_verification:
            if verification_code == email_verification.verification_code and email_verification.expiration_date > timezone.now():
                email_verification.is_verified = True
                email_verification.save()
                
                unverified_group = Group.objects.get(name="Unverified Email")
                user_verified_group, created = Group.objects.get_or_create(name="Verified")
                user.groups.remove(unverified_group)
                user.groups.add(user_verified_group)
                user.is_onboarded = True
                user.save()
                
                messages.success(request, "Email verified successfully!")
                login(request, request.user)
                return redirect("accountManagement:userPreferences")
            else:
                messages.error(request, "Invalid verification code.")
        else:
            messages.error(request, "No email record found.")
    return render(request, "authenticationApp/onboarding.html")


@login_required
def startVerificationProcess(request):
    group, created = Group.objects.get_or_create(name="Unverified Email")
    user = request.user
    user.groups.add(group)
    user.save()
    messages.info(request, "Verification email sent successfully!")
    generateVerficationLink(request, user)
    return render(request, "authenticationApp/verify/verificationLinkSent.html")



def loginView(request):
    if request.method == "POST":
        form = UserAuthenticationForm(data=request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = authenticate(request, email=email, password=password)

            if user is not None:
                login(request, user)
                login_history = LoginHistoryModel.objects.create(
                    user=user,
                    email=user.email,
                    ip_address=request.META.get("REMOTE_ADDR"),
                )
                login_history.save()
                next_url = request.GET.get("next", "accountManagement:userAccount")
                return redirect(next_url)
            else:
                form.add_error(None, "Invalid email or password")
    else:
        form = UserAuthenticationForm()
    return render(request, "authenticationApp/login.html", {"form": form})


@login_required(login_url="authentication:login")
def logoutView(request):
    try:
        login_history = LoginHistoryModel.objects.filter(user=request.user).latest(
            "login_time"
        )
        login_history.end_session()
    except LoginHistoryModel.DoesNotExist:
        pass

    logout(request)
    return redirect("core:index")


from datetime import timedelta

ResetLinkExpiryTime = timedelta(hours=2)


def forgotPasswordView(request):
    if request.method == "POST":
        emailForm = EmailPasswordResetForm(request.POST)
        if emailForm.is_valid():
            email = emailForm.cleaned_data["email"]
            user = CustomUser.objects.filter(email=email).first()
            if user:
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))

                expiry_time = timezone.now() + ResetLinkExpiryTime

                reset_url = request.build_absolute_uri(
                    reverse(
                        "authentication:passwordReset",
                        kwargs={"uidb64": uid, "token": token},
                    )
                )

                # Including expiry time in reset url link
                reset_url += f"?expires={expiry_time.timestamp()}"

                subject = "Request to reset password | WAVE."
                message = render_to_string(
                    "authenticationApp/passwordReset/email/resetEmailTemplate.html",
                    {"reset_url": reset_url},
                )
                send_mail(subject, message, None, [email])
                messages.success(request, "Email sent successfully!")
            else:
                messages.error(request, "Account does not exist")
                return redirect("authentication:forgot")
        else:
            for field, error_list in emailForm.errors.items():
                for error in error_list:
                    messages.error(request, f"{error}")
            return redirect("authentication:forgot")
    else:
        emailForm = EmailPasswordResetForm()
    return render(
        request,
        "authenticationApp/passwordReset/forgot_password.html",
        {"emailForm": emailForm},
    )


def setNewPassword(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        # Get expiry time from query parameters
        expiry_timestamp = request.GET.get("expiry")
        if expiry_timestamp:
            expirty_time = datetime.fromtimestamp(float(expiry_timestamp))
            current_time = timezone.now()

            if current_time > expirty_time:
                # Set up a front end page to display "Link has expired"
                return HttpResponse("Password reset link expired.")

        if request.method == "POST":
            form = NewPasswordForm(request.POST)
            if form.is_valid():
                password = form.cleaned_data.get("password")
                user.set_password(password)
                user.save()

                login(request, user)
                return redirect("accountManagement:userAccount")
        else:
            form = NewPasswordForm()
        return render(
            request,
            "authenticationApp/passwordReset/newPassword.html",
            {"form": form, "uidb64": uidb64, "token": token},
        )
    else:
        # Handle invalid or expired link
        return render(request, "extras/invalid/invalid.html")
