from django.shortcuts import render, redirect

# Create your views here.
def mainSupportView(request):
    return render(request, "supportCenterApp/support.html")