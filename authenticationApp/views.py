import datetime
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordResetConfirmView
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.shortcuts import render, redirect, HttpResponse
from .forms import (
    CustomUserJoinForm,
    UserAuthenticationForm,
    EmailPasswordResetForm,
    NewPasswordForm,
)
from django.contrib.auth import login, logout, authenticate
from .models import CustomUser
from adminDashboardApp.models import LoginHistoryModel

# from django.http import HttpResponse


# Create your views here.
def joinView(request):
    if request.method == "POST":
        form = CustomUserJoinForm(request.POST)
        if form.is_valid():
            print("Form is valid!")
            user = form.save()
            login(request, user)
            return redirect("accountManagement:userAccount")
        else:
            print(form.errors)
    else:
        form = CustomUserJoinForm()
    return render(request, "authenticationApp/join.html", {"form": form})


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
                return redirect("accountManagement:userAccount")
            else:
                form.add_error(None, "Invalid email or password")
    else:
        form = UserAuthenticationForm()
    return render(request, "authenticationApp/login.html", {"form": form})


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
                reset_url += f'?expires={expiry_time.timestamp()}'

                subject = "Request to reset password | WAVE."
                message = render_to_string(
                    "authenticationApp/passwordReset/email/resetEmailTemplate.html",
                    {"reset_url": reset_url},
                )
                send_mail(subject, message, None, [email])
                messages.success(request, 'Email sent successfully!')
            else:
                messages.error(request, 'Account does not exist')
                return redirect("authentication:forgot")
        else:
            for field, error_list in emailForm.errors.items():
                for error in error_list:
                    messages.error(request, f'{error}')
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
        expiry_timestamp = request.GET.get('expiry')
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
            request, "authenticationApp/passwordReset/newPassword.html", {"form": form, 'uidb64': uidb64, 'token':token}
        )
    else:
        # Handle invalid or expired link
        return render(request, "extras/invalid/invalid.html")
