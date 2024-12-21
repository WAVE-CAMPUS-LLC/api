from enum import member
from django.utils import timezone
from django.urls import reverse
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.core.signing import BadSignature, Signer
from django.core.exceptions import PermissionDenied
from django.contrib.auth import logout
from django.contrib.auth.models import Group, Permission
from django.contrib.auth import get_user_model
from eventManagementApp.models import Event

from accountManagementApp.models import UserProfile
from authenticationApp.models import CustomUser
from collegeManagementApp.models import Membership, Organization, CollegeEventLink
from .models import CampusManagerInvite
from adminDashboardApp.models import College
from wave_v1.decorators import campusManagerRequired


User = get_user_model()

# Create your views here.
@login_required
@campusManagerRequired("Campus Manager")
def managerDashboardView(request):
    """
    The `managerDashboardView` function is a Django view that displays managed colleges and pending
    organizations for a campus manager, allowing them to approve or decline pending organizations.

    :param request: The `request` parameter in the `managerDashboardView` function is an HttpRequest
    object that represents the current HTTP request. It contains information about the request made by
    the client, such as the request method (GET, POST, etc.), user session data, and any data sent in
    the request (e
    :return: The `managerDashboardView` function returns a rendered HTML template named
    "campusManagerApp/managerDashboard.html" along with context data including the managed colleges and
    pending organizations.
    """

    college = get_object_or_404(College, managers=request.user)
    college_event_links = CollegeEventLink.objects.filter(college=college)
    
    events = [link.event for link in college_event_links]

    member_count = Membership.objects.filter(college=college).count()
    organization_count = Organization.objects.filter(college=college).count()
    

    pending_organizations = Organization.objects.filter(
        status="Pending", college__collegeId=college.collegeId
    )

    if request.method == "POST":
        orgId = request.POST.get("orgId")
        action = request.POST.get("approvalAction")
        event_id = request.POST.get("event_id")

        organization = get_object_or_404(
            Organization, orgId=orgId, status="Pending", college=college
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
            "college": college,
            "events": events,
            "member_count": member_count,
            "organization_count": organization_count,
            "pending_organizations": pending_organizations,
        },
    )


@login_required
@campusManagerRequired("Campus Manager")
def managedCampusView(request, collegeId):
    college = get_object_or_404(College, managers=request.user, collegeId=collegeId)
    organizations = Organization.objects.filter(college=college)
    members = UserProfile.objects.filter(college=college)
    
    college_event_links = CollegeEventLink.objects.filter(college=college)
    
    events = [link.event for link in college_event_links]
    
    if request.method == "POST":
        action=request.POST.get("action")
        organizationID = request.POST.get("organizationID")
        event_id = request.POST.get("event_id")
        
        
        if action == "deleteOrganization":
            organization = get_object_or_404(Organization, orgId=organizationID)
            organization.delete()
            messages.success(request, "Organization deleted.")
            return redirect("campusManager:campus", collegeId=collegeId)
        
        elif action == "removeCampusMember":
            memberEmail = request.POST.get("memberEmail")
            if memberEmail:
                user = get_object_or_404(User, email=memberEmail)
                user_profile = get_object_or_404(UserProfile, user=user)
                if user_profile.college and str(user_profile.college.collegeId) == str(collegeId):
                    user_profile.college = None
                    user_profile.save()
                    messages.success(request, f"User {user.email} removed from college.")
            return redirect("campusManager:campus", collegeId=collegeId)
        
        
        elif action == "pause" and event_id:
            try:
                event = get_object_or_404(Event, eventId=event_id)
                event.admin_status = "paused"
                event.save()
                messages.success(request, "Event paused.")
                return redirect("campusManager:campus", collegeId=college.collegeId)
            except Event.DoesNotExist:
                messages.error(request, "Event not found.")
                
        elif action == "activate" and event_id:
            try:
                event = get_object_or_404(Event, eventId=event_id)
                event.admin_status = "active"
                event.save()
                messages.success(request, "Event activated.")
                return redirect("campusManager:campus", collegeId=college.collegeId)
            except Event.DoesNotExist:
                messages.error(request, "Event not found.")
                
        elif action == "delete" and event_id:
            try:
                event = get_object_or_404(Event, eventId=event_id)
                event.delete()
                messages.success(request, "Event deleted.")
                return redirect("campusManager:campus", collegeId=college.collegeId)
            except Event.DoesNotExist:
                messages.error(request, "Event not found.")
    
                
                
    return render(
        request,
        "campusManagerApp/managerCampusView.html",
        {
            "college": college,
            "organizations": organizations,
            "collegeMembers": members,
            "events": events,
        },
    )


def accept_invite(request, token, collegeId):
    """
    The function `accept_invite` accepts an invitation for a user to become a campus manager at a
    college, handling authentication, user groups, and session data.

    :param request: The `request` parameter in the `accept_invite` function is typically an HttpRequest
    object that represents the current request from the user's browser. It contains metadata about the
    request, such as headers, cookies, and user session information. The function uses the `request`
    object to access user authentication status,
    :param token: The `token` parameter in the `accept_invite` function is used to identify and retrieve
    a CampusManagerInvite object with a specific token value. This token is typically generated and
    included in the invite link sent to the user. It helps in verifying the authenticity of the invite
    and ensuring that it has not
    :param collegeId: The `collegeId` parameter in the `accept_invite` function is used to identify the
    specific college for which the invite is being accepted. It is used to retrieve the
    CampusManagerInvite object associated with the given collegeId and token
    :return: The `accept_invite` function returns a redirect response to different URLs based on the
    conditions met during the execution of the function.
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
            campusManager_group, created = Group.objects.get_or_create(
                name="Campus Manager"
            )
            if not college:
                messages.error(request, "The associated college could not be found.")
                return redirect("core:index")
            print(college.name)
            college.managers.add(request.user)
            inviteUser = CustomUser.objects.get(email=invite_email)
            inviteUser.groups.add(campusManager_group)
            print(
                f"{inviteUser.first_name} {inviteUser.last_name} has had the campus manager role added to account."
            )
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
    
@login_required
def college_detail_view(request, collegeId):  # Changed from college_id to collegeId
    college = get_object_or_404(College, collegeId=collegeId)  # Using collegeId instead of id
    events = Event.objects.all()
    
    context = {
        'college': college,
        'events': events,
    }
    return render(request, 'adminDashboardApp/tabs/colleges/collegeInfo.html', context)
