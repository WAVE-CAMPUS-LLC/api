import datetime
import random
from datetime import timedelta
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.contrib.auth.views import PasswordResetConfirmView
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string, get_template
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.html import strip_tags
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
from stripeManagementApp.customerSetup import CustomerAccount
from campusManagerApp.models import CampusManagerInvite
from django.contrib.auth.models import Group
from django.conf import settings

from wave_v1.decorators import check_suspension, emailUnverified


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

            unverified_group, created = Group.objects.get_or_create(name="Unverified")
            member, created = Group.objects.get_or_create(name="Member")
            user.groups.add(unverified_group)
            user.groups.add(member)

            verification_code = generateVerificationCode()
            expiration_time = timezone.now() + timedelta(hours=12)
            email_verification = EmailVerification.objects.create(
                user=user,
                verification_code=verification_code,
                expiration_date=expiration_time,
            )

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
            user.email_verified = False

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
            if not user.customer_id:
                customer = CustomerAccount.createCustomerAccount(
                    request, user.email, user.first_name, user.last_name
                )
                if customer:
                    user.customer_id = customer["id"]
                    user.save()
                else:
                    messages.error(
                        request, "Failed to create customer account. Please try again."
                    )
                    return redirect("authentication:join")

            messages.info(request, "A verification code has been sent to your email.")
            login(request, user)
            next_url = request.GET.get("next", "authentication:verifyEmail")
            return redirect(next_url)
        else:
            messages.error(request, "Invalid form")
    else:
        form = CustomUserJoinForm()
    return render(request, "authenticationApp/join.html", {"form": form})


@login_required
@emailUnverified
def emailVerifyView(request):
    if request.method == "POST":
        try:
            action = request.POST.get("action")
            verification_code = request.POST.get("verification_code")
            print(f"Action: {action}, Code: {verification_code}")

            email_verification = EmailVerification.objects.filter(
                user=request.user, is_verified=False
            ).first()
            user = CustomUser.objects.get(email=request.user.email)

            if action == "verifyEmailCode":
                if email_verification:
                    if (
                        verification_code == email_verification.verification_code
                        and email_verification.expiration_date > timezone.now()
                    ):
                        email_verification.is_verified = True
                        email_verification.save()

                        # Get or create the groups
                        unverified_group, _ = Group.objects.get_or_create(
                            name="Unverified"
                        )
                        user_verified_group, _ = Group.objects.get_or_create(
                            name="Verified"
                        )

                        # Update user groups
                        user.groups.remove(unverified_group)
                        user.groups.add(user_verified_group)
                        user.email_verified = True
                        user.save()

                        messages.success(request, "Email verified successfully!")
                        login(request, request.user)
                        return redirect("accountManagement:userAccount")
                    else:
                        messages.error(request, "Invalid verification code.")
                else:
                    messages.error(request, "No email record found.")
            elif action == "sendEmailCode":
                if not email_verification:
                    print("No EmailVerification record found.")
                    email_verification = EmailVerification.objects.create(
                        user=request.user,
                        verification_code=generateVerificationCode(),
                        expiration_date=timezone.now() + timedelta(hours=12),
                    )
                else:
                    print("EmailVerification record found.")
                    email_verification.verification_code = generateVerificationCode()
                    email_verification.expiration_date = timezone.now() + timedelta(
                        hours=12
                    )
                    email_verification.save()

                try:
                    template = get_template(
                        "emailManagement/build_production/emails/authenticationApp/verifyEmail.html"
                    )
                    emailMessage = template.render(
                        {"verification_code": email_verification.verification_code}
                    )

                    plainMessage = strip_tags(emailMessage)
                    send_mail(
                        subject="Welcome to WAVE.! Verify your email",
                        message=plainMessage,
                        from_email=None,
                        recipient_list=[user.email],
                        fail_silently=False,
                        html_message=emailMessage,
                    )
                    messages.success(request, "Verification code sent successfully!")
                except Exception as e:
                    messages.error(
                        request, "Failed to send verification code. Please try again."
                    )
                    print(f"Error sending email: {e}")
            else:
                messages.error(request, "Invalid action.")
        except Exception as e:
            print(f"Error in emailVerifyView: {str(e)}")
            messages.error(request, "An error occurred. Please try again.")
    return render(request, "authenticationApp/verifyEmail.html")


def loginView(request):
    if request.method == "POST":
        form = UserAuthenticationForm(data=request.POST)
        if form.is_valid():
            identifier = form.cleaned_data["identifier"]
            password = form.cleaned_data["password"]

            # Check if the identifier is an email or username
            user = (
                CustomUser.objects.filter(email=identifier).first()
                or CustomUser.objects.filter(username=identifier).first()
            )

            if user:
                user = authenticate(
                    request, email=user.email, password=password
                )  # Authenticate using email
                if user:
                    # Create or find Stripe customer before logging in
                    if not user.customer_id:
                        existing_customer = CustomerAccount.searchCustomerAccount(user.email)
                        if existing_customer:
                            user.customer_id = existing_customer.id
                            user.save()
                        else:
                            new_customer = CustomerAccount.createCustomerAccount(
                                request, user.email, user.first_name, user.last_name
                            )
                            if new_customer:
                                user.customer_id = new_customer.id
                                user.save()
                            else:
                                messages.warning(request, "Failed to set up payment processing. You can try again in your account settings.")

                    login(request, user)
                    LoginHistoryModel.objects.create(
                        user=user,
                        email=user.email,
                        ip_address=request.META.get("REMOTE_ADDR"),
                    )

                    next_url = request.GET.get("next")
                    if (
                        next_url
                        and next_url.strip()
                        and not next_url.startswith("http")
                    ):
                        return redirect(next_url)

                    return redirect("accountManagement:userAccount")

            form.add_error(None, "Invalid email/username or password")
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
