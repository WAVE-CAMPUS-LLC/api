from django.utils import timezone
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.core.signing import BadSignature, Signer
from django.core.exceptions import PermissionDenied

from authenticationApp.models import CustomUser
from .models import CampusManagerAssignment, CampusManagerInvite
from adminDashboardApp.models import College


# Create your views here.
@login_required
def managerDashboardView(request):
    if not College.objects.filter(managers=request.user).exists():
        raise PermissionDenied("You are not a campus manager.")

    managed_colleges = College.objects.filter(managers=request.user).annotate(
        member_count=Count("membership")
    )

    return render(
        request,
        "campusManagerApp/managerDashboard.html",
        {"managed_colleges": managed_colleges},
    )


def accept_invite(request, token, collegeId):
    # Find the invite using the token and college
    try:
        invite = CampusManagerInvite.objects.get(
            token=token, college__collegeId=collegeId, accepted=False
        )
    except CampusManagerInvite.DoesNotExist:
        messages.error(request, "Invalid or expired invite link.")
        return redirect("core:index")

    # Retrieve the college and email from the invite
    college = invite.college
    email = invite.email

    # Check if the user exists
    user = CustomUser.objects.filter(email=email).first()

    if user:
        # If the user exists, assign them as a manager and mark invite as accepted
        college.managers.add(user)
        invite.accepted = True
        invite.save()
        messages.success(request, f"Successfully joined {college.name} as a manager.")
        return redirect("campusManager:dashboard")
    else:
        # If the user does not exist, save invite data in session and redirect to sign up
        request.session["invite_email"] = email
        request.session["collegeId"] = collegeId
        request.session["invite_token"] = token
        return redirect("authentication:join")


def decline_invite(request, token):
    invite = get_object_or_404(CampusManagerInvite, token=token, accepted=False)
    invite.delete()  # Delete the invite if declined
    return redirect("home")
