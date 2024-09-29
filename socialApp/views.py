from http.client import HTTPResponse
from os import name
import re
from datetime import datetime
from turtle import st
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponseRedirect
from django.template import RequestContext
from django.template.loader import render_to_string 
from accountManagementApp.models import UserProfile
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from .models import FriendRequest, Crew, CrewMember, CrewRequest
from django.db.models import Q
from .forms import createCrewForm

# Decorators to check user roles and permissions
from wave_v1.decorators import member_required, check_suspension

UserModel = get_user_model()


# Create your views here.
@login_required
def socialHomeView(request):
    user = get_object_or_404(UserProfile, user=request.user)
    my_crews = Crew.objects.filter(members__user=request.user)
    time = datetime.now().timestamp()

    pending_friend_requests = FriendRequest.objects.filter(
        receiver=request.user, status="pending"
    )
    pending_crew_requests = CrewRequest.objects.filter(
        receiver=request.user, status="pending"
    )
                
    friends = user.friends.all() 
    
    print("DEBUG: Friends of user ", list(friends))
    
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "acceptRequest":
            friend_request_id = request.POST.get("friend_request_id")  
            friend_request = FriendRequest.objects.get(requestId=friend_request_id, receiver=request.user)
            sender = get_object_or_404(UserProfile, user=friend_request.sender)
            user.friends.add(sender) 
            sender.friends.add(user) 
            friend_request.accept_request()

        elif action == "declineRequest":
            friend_request_id = request.POST.get("friend_request_id")
            friend_request = FriendRequest.objects.get(requestId=friend_request_id, receiver=request.user)
            sender = get_object_or_404(UserProfile, user=friend_request.sender)
            user.friends.remove(sender)
            sender.friends.remove(user)
            friend_request.decline_request()
            
        else:
            crew_id = request.POST.get("crew_id")
            crew_invite_action(request, crew_id, action)
        
    return render(
        request,
        "socialApp/socialHome.html",
        {"pending_friend_requests": pending_friend_requests, "pending_crew_requests": pending_crew_requests, "friends": friends, "my_crews": my_crews, "time": time},
    )

def crew_invite_action(request, crew_id, action):
    crew = get_object_or_404(Crew, crewId=crew_id)
    crew_request = get_object_or_404(CrewRequest, crew=crew, receiver=request.user)
    
    if action == "joinCrew":
        crew_request.accept_request()
        CrewMember.objects.create(user=request.user, crew=crew)
        messages.success(request, f'{request.user} joined the {crew.name} crew.')
    elif action == "declineCrew":
        crew_request.decline_request()
        messages.success(request, f'{request.user} has declines the invite to join {crew.name} crew.')
        
    return redirect('social:home')


def publicProfileView(request, username):
    try:
        user = get_object_or_404(UserModel, username=username)
        # Ensure user_profile exists or create it if it doesn't
        user_profile, created = UserProfile.objects.get_or_create(user=user)

        friend_request = FriendRequest.objects.filter(
            (Q(sender=request.user) & Q(receiver=user))
            | (Q(sender=user) & Q(receiver=request.user))
        ).first()

        friend_request_status = None
        if friend_request:
            friend_request_status = friend_request.status

        is_profile = request.user == user

        if request.method == "POST":
            action = request.POST.get("action")
            if action == "send_request":
                success, message = send_friend_request(request.user, user_profile)

                if success:
                    messages.success(request, message)
                    return redirect("social:publicProfile", username=username)
                else:
                    messages.warning(request, message)
                    return redirect("social:publicProfile", username=username)
            elif (
                action == "cancel_request"
                and friend_request
                and friend_request_status == "pending"
            ):
                friend_request.delete()
                messages.success(request, "Friend request canceled.")
                friend_request_status = None
                return redirect("social:publicProfile", username=username)

            elif (
                action == "remove_request"
                and friend_request
                and friend_request_status == "accepted"
            ):
                friend_request.delete()
                messages.success(request, "Friend removed.")
                friend_request_status = None
                return redirect("social:publicProfile", username=username)

    except Http404:
        return render(request, "extras/invalid/invalid.html")

    return render(
        request,
        "socialApp/publicProfile.html",
        {
            "user": user,
            "user_profile": user_profile,
            "friend_request_status": friend_request_status,
            "is_profile": is_profile,
        },
    )


def send_friend_request(sender, receiver_username):
    receiver = get_object_or_404(UserProfile, user__username=receiver_username)

    if sender.user_profile.is_friends_with(receiver.user):
        return False, "You are already friends."
    
    if sender.user_profile.has_pending_request(receiver.user):
        return False, "A friend request is already pending."

    friend_request, created = FriendRequest.objects.get_or_create(
        sender=sender, receiver=receiver.user, defaults={"status": "pending"}
    )

    if not created:
        return False, "Friend request has already been sent."

    return True, "Friend request sent successfully."


def send_crew_request(sender, receiver_username, crew_id):
    sender = get_object_or_404(UserProfile, user__username=sender.user.username)
    receiver = get_object_or_404(UserProfile, user__username=receiver_username)
    crew = get_object_or_404(Crew, crewId=crew_id)
    
    # Ensure receiver isn't already in the crew
    if CrewMember.objects.filter(crew=crew, user=receiver.user).exists():
        return False, "User is already a member of the crew.", None

    # Send a crew request
    crew_request, created = CrewRequest.objects.get_or_create(
        sender=sender.user, receiver=receiver.user, crew=crew, defaults={"status": "pending"}
    )

    if not created:
        return False, "Crew request has already been sent.", crew_request

    return True, "Crew request sent successfully.", crew_request


@login_required
def createCrewView(request):
    pageName = "social"

    if request.method == "POST":
        crewForm = createCrewForm(request.POST)

        if crewForm.is_valid():
            crew_instance = crewForm.save(commit=False)
            crew_instance.created_by = request.user
            crew_instance.save()

            CrewMember.objects.create(
                user=request.user,
                crew=crew_instance,
                is_admin=True,
            )

            return redirect("social:home")

    else:
        crewForm = createCrewForm()

    return render(request, "socialApp/crews/createCrew.html", {"crewForm": crewForm})


@login_required
def crewView(request, crewId):
    user = get_object_or_404(UserProfile, user=request.user)
    print(f"DEBUG: Logged in user: {user.user.username}")  # Debugging user

    crew = get_object_or_404(Crew, crewId=crewId)
    print(f"DEBUG: Crew fetched: {crew.name}")  # Debugging crew details

    crewMembers = CrewMember.objects.filter(crew=crew)
    if not crewMembers:
        print(f"DEBUG: No crew members found for crew {crewId}")  # Debugging crew members
    else:
        print(f"DEBUG: Crew members count: {crewMembers.count()}")
    
    friends = user.friends.all()
    friends_not_in_crew = friends.exclude(user__in=crewMembers.values_list('user', flat=True))
    time = datetime.now().timestamp()
    print(f"DEBUG: Friends not in crew count: {friends_not_in_crew.count()}")
    
    if request.method == "POST":
        action = request.POST.get("action")
        inviteeUsername = request.POST.get("invitee_username")
        if action == "crew_invite":
            success, message, crew_request = send_crew_request(user, inviteeUsername, crewId)
            print("DEBUG: POST request received")
            

            if success:
                messages.success(request, message)
            else:
                messages.warning(request, message)
    else:
        crew_request = None
    
    status = crew_request.status if crew_request else None
        
    return render(request, "socialApp/crews/crew.html", {'crew': crew, 'crewMembers': crewMembers, 'status': status, "friendsNotInCrew": friends_not_in_crew, 'time': time})

    # if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
    #     query = request.GET.get('query', '')
        
    #     user_friends = user.friends.all()

    #     # Filter friends based on the search query (e.g., name)
    #     results = user_friends.filter(
    #         Q(user__username__icontains=query) | 
    #         Q(user__first_name__icontains=query) | 
    #         Q(user__last_name__icontains=query)
    #     )


    #     # Render each result using the template
    #     if results.exists():
    #         results_html = []
    #         for friend in results:
    #             html = render_to_string('socialApp/extras/search-item.html', {'friend': friend, "time": time, "crew": crew}, request=request)
    #             results_html.append(html)
    #         return JsonResponse({'results_html': results_html, 'no_results': False})
    #     else:
    #         no_results_html = render_to_string('socialApp/extras/no-result.html')
    #         return JsonResponse({'results_html': [], 'no_results': True, 'no_results_html': no_results_html})