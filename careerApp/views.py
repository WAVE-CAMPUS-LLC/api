from django.shortcuts import render, redirect

# Create your views here.
def careerHomeApp(request):
    pageName = "Careers"
    return render(request, "careerApp/careers.html", {"pageName": pageName})