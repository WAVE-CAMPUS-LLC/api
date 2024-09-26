from django.utils import timezone
from django.urls import reverse
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.core.signing import BadSignature, Signer
from django.core.exceptions import PermissionDenied
from django.contrib.auth import logout

from authenticationApp.models import CustomUser
from collegeManagementApp.models import Organization
from .models import CampusManagerInvite
from adminDashboardApp.models import College


# Create your views here.
@login_required
def managerDashboardView(request):
    managed_colleges = College.objects.filter(managers=request.user).annotate(
        member_count=Count("membership")
    )

    pending_organizations = Organization.objects.filter(
        status="Pending", college__in=managed_colleges
    )

    if request.method == "POST":
        orgId = request.POST.get("orgId")
        action = request.POST.get("approvalAction")

        organization = get_object_or_404(
            Organization, orgId=orgId, status="Pending", college__in=managed_colleges
        )

        if action == "approveOrg":
            organization.status = "Accepted"
            organization.save()
            messages.success(
                request, f"Organization '{organization.name}' has been approved."
            )
        elif action == "declineOrg":
            organization.status = "Denied"
            organization.save()
            messages.success(
                request, f"Organization '{organization.name}' has been declined."
            )

        return redirect("campusManager:dashboard")

    return render(
        request,
        "campusManagerApp/managerDashboard.html",
        {
            "managed_colleges": managed_colleges,
            "pending_organizations": pending_organizations,
        },
    )


def accept_invite(request, token, collegeId):
    """
    The function `accept_invite` accepts an invitation to become a campus manager for a specific
    college.

    :param request: The `request` parameter in the `accept_invite` function is typically an HttpRequest
    object that represents the current HTTP request. It contains metadata about the request, such as
    headers, method, user session, and more. This parameter allows the function to interact with the
    current request and response cycle in a Django
    :param token: A token is a unique string of characters that is used for authentication and
    authorization purposes. In this context, the token is likely a unique identifier associated with a
    Campus Manager invite. It helps in verifying the authenticity of the invite and ensuring that it has
    not been tampered with or expired
    :param collegeId: The `collegeId` parameter in the `accept_invite` function is used to identify the
    specific college for which the invite is being accepted. It is used to retrieve the
    CampusManagerInvite object associated with the given collegeId and token
    :return: The `accept_invite` function returns a redirect response to a specific URL based on the
    conditions met within the function. The specific URL to which the function redirects depends on
    whether the user is authenticated, the email matches the invite email, and whether the invite is
    successfully accepted.
    """
    try:
        invite = CampusManagerInvite.objects.get(
            token=token, college__collegeId=collegeId, accepted=False
        )
    except CampusManagerInvite.DoesNotExist:
        messages.error(request, "Invalid or expired invite link.")
        return redirect("core:index")

    college = invite.college
    invite_email = invite.email

    if request.user.is_authenticated:
        if request.user.email != invite_email:
            messages.error(
                request,
                f"You are logged in as {request.user.email}. Please log in with {invite_email} to accept the invite.",
            )
            logout(request)
            return redirect(f"{reverse('authentication:login')}?next={request.path}")
        else:
            college.managers.add(request.user)
            invite.accepted = True
            invite.save()
            messages.success(
                request, f"Successfully joined {college.name} as a manager."
            )
            return redirect("campusManager:dashboard")
    else:
        request.session["invite_email"] = invite_email
        request.session["collegeId"] = collegeId
        request.session["invite_token"] = token
        return redirect(f"{reverse('authentication:login')}?next={request.path}")
