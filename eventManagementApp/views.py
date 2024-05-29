from django.shortcuts import render

# Create your views here.
def hostApplyView(request):
    return render(request, "eventManagementApp/host/hostApplication.html")