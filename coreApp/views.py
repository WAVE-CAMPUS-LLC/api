from django.shortcuts import render

# Create your views here.
def indexView(request):
    pageName = "home"
    return render(request, 'coreApp/index.html', {'page': pageName})

def exploreView(request):
    pageName = "explore"
    return render(request, "coreApp/explore.html", {'page':pageName})

def eventDetailsView(request):
    pageName = "explore"
    return render(request, "coreApp/eventDetails.html", {'page':pageName})