from django.shortcuts import render

# Create your views here.
def blogHomeView(request):
    pageName = "Blog"
    return render(request, "blogApp/home.html", {"pageName": pageName})