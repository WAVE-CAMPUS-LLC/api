import datetime
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
from .models import CustomUser
from adminDashboardApp.models import College, LoginHistoryModel
from campusManagerApp.models import CampusManagerInvite
from django.contrib.auth.models import Group

from wave_v1.decorators import (
    check_suspension,
)


# Create your views here.
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

            generateVerficationLink(request, user)

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
                return redirect("campusManager:dashboard")

            login(request, user)
            return redirect("accountManagement:userPreferences")
        else:
            print(form.errors)
    else:
        form = CustomUserJoinForm()
    return render(request, "authenticationApp/join.html", {"form": form})


def generateVerficationLink(request, user):
    signer = TimestampSigner()
    token = signer.sign(user.email)

    verification_link = request.build_absolute_uri(
        reverse("authentication:verify", kwargs={"token": token})
    )

    email_content = render_to_string(
        "emailTemplates/authenticationApp/verify/verifyEmail.html",
        {"verification_link": verification_link, "user": user},
    )
    send_mail(
        subject="Verify your email",
        message="Please verify your email address.",
        from_email="admin@wavecampus.net",
        recipient_list=[user.email],
        html_message=email_content,
        fail_silently=False,
    )
    print(f"Email sent to {user.email} with verification link: {verification_link}")


@login_required
def verifyEmail(request, token):
    """
    The function `verifyEmail` verifies a user's email address using a token and updates the user's
    email verification status in the database.
    """
    signer = TimestampSigner()
    try:
        email = signer.unsign(token, max_age=86400) 

        if request.user.email != email:
            return redirect("authentication:login")

        user = CustomUser.objects.get(email=email)

        user.email_verified = True
        user.groups.remove(Group.objects.get(name="Unverified Email"))
        user.save()

        return redirect("accountManagement:userPreferences")

    except (SignatureExpired, BadSignature, CustomUser.DoesNotExist):
        return render(
            request, "emailTemplates/authenticationApp/verify/verificationExpired.html"
        )


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
