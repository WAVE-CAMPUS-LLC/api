from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from wave_v1.decorators import (
    check_suspension,
    member,
    verified,
    onboarded,
    admin,
    superAdmin,
)

from .userAnalytics import UserAnalytics


# Create your views here.
@login_required(login_url="authentication:login")
@check_suspension
@member
@admin
def analyticsHome(request):
    return render(request, "dataAnalytics/home.html")

@login_required(login_url="authentication:login")
@check_suspension
@member
@admin
def userSignups(request):
    return render(request, "dataAnalytics/userAnalytics/userSignups.html")

@login_required(login_url="authentication:login")
@check_suspension
@member
@admin
def userDemographics(request):
    return render(request, "dataAnalytics/userAnalytics/userDemographics.html")


def userAnalytics(request):
    return render(request, "dataAnalytics/userAnalytics.html")


def user_count_api(request):
    return UserAnalytics().getUserCount()
