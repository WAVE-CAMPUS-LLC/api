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



# Create your views here.
@login_required(login_url="authentication:login")
@check_suspension
@member
@admin
def analyticsHome(request):
    return render(request, "dataAnalyticsApp/home.html")



'''
User Analytics
'''
@login_required(login_url="authentication:login")
@check_suspension
@member
@admin
def userSignups(request):
    return render(request, "dataAnalyticsApp/userAnalytics/userSignups.html")


@login_required(login_url="authentication:login")
@check_suspension
@member
@admin
def userLogins(request):
    return render(request, "dataAnalyticsApp/userAnalytics/userLogins.html")


@login_required(login_url="authentication:login")
@check_suspension
@member
@admin
def userDemographics(request):
    return render(request, "dataAnalyticsApp/userAnalytics/userDemographics.html")



'''
College Analytics
'''

@login_required(login_url="authentication:login")
@check_suspension
@member
@admin
def collegeOverview(request):
    return render(request, "dataAnalyticsApp/collegeAnalytics/collegeOverview.html")


@login_required(login_url="authentication:login")
@check_suspension
@member
@admin
def collegeMembership(request):
    return render(request, "dataAnalyticsApp/collegeAnalytics/collegeMembership.html")


@login_required(login_url="authentication:login")
@check_suspension
@member
@admin
def organizationOverview(request):
    return render(request, "dataAnalyticsApp/collegeAnalytics/organizationOverview.html")


@login_required(login_url="authentication:login")
@check_suspension
@member
@admin
def organizationMembership(request):
    return render(request, "dataAnalyticsApp/collegeAnalytics/organizationMembership.html")