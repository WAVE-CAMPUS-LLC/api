from http.client import HTTPResponse
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from accountManagementApp.models import UserProfile

# Decorators to check user roles and permissions
from wave_v1.decorators import member_required, check_suspension

UserModel = get_user_model()

# Create your views here.
@login_required
def socialHomeView(request):
    return render(request, "socialApp/socialHome.html")


def publicProfileView(request, username):
    try:
        user = get_object_or_404(UserModel, username=username)

    except Http404:
        return render(request, "extras/invalid/invalid.html")
    
    
    return render(request, "socialApp/publicProfile.html", {'user': user})