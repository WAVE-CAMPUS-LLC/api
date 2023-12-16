from django.shortcuts import render

# Create your views here.
def userAccountView(request):
    return render(request, 'accountManagementApp/profileManagement.html')