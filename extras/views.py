from django.shortcuts import render, redirect

# Create your views here.
def aboutView(request):
    return render(request, "extras/company/about.html")

def careersView(request):
    return render(request, "extras/company/careers.html")

def newsroomView(request):
    return render(request, "extras/company/newsroom.html")

def teamView(request):
    return render(request, "extras/company/team.html")


def faqView(request):
    return render(request, "extras/policy/faq.html")

def privacyView(request):
    return render(request, "extras/policy/privacy.html")

def safetyView(request):
    return render(request, "extras/policy/safety.html")

def termsView(request):
    return render(request, "extras/policy/terms.html")


def collegesView(request):
    return render(request, "extras/resources/colleges.html")

def creatorsView(request):
    return render(request, "extras/resources/creators.html")

def organizersView(request):
    return render(request, "extras/resources/organizers.html")

def partnersView(request):
    return render(request, "extras/resources/partners.html")