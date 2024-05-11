from django.shortcuts import render

# Create your views here.
def indexView(request):
    return render(request, 'coreApp/index.html')

def exploreView(request):
    return render(request, "coreApp/explore.html")