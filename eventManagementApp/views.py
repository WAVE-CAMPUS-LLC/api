from django.shortcuts import render

# Create your views here.
def hostView(request):
    pageName = "Host Event"
    return render(request, "eventManagementApp/host/hostHome.html", {"pageName": pageName})


def hostApplyView(request):
    return render(request, "eventManagementApp/host/hostApplication.html")