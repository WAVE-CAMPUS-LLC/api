from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


# Create your views here.
# views.py
@login_required
def profileView(request):
    return render(request, "accountManagementApp/profileManagement.html")

@login_required
def settingsView(request):
    return render(request, 'accountManagementApp/profileSettings.html')
