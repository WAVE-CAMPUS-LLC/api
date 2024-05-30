from django.shortcuts import render, redirect

# Create your views here.


def aboutView(request):
    pageName = "About"
    return render(request, "extras/company/about.html", {"pageName": pageName})


def newsroomView(request):
    pageName = "Newsroom"
    return render(request, "extras/company/newsroom.html", {"pageName": pageName})

def newsView(request):
    return render(request, "extras/company/newsroom/news.html")


def teamView(request):
    pageName = "Our Team"
    return render(request, "extras/company/team.html", {"pageName": pageName})


def faqView(request):
    pageName = "Frequently Asked"
    return render(request, "extras/policy/faq.html", {"pageName": pageName})

def privacyView(request):
    pageName = "Privacy Policy"
    return render(request, "extras/policy/privacy.html", {"pageName": pageName})

def safetyView(request):
    pageName = "Safety Policy"
    return render(request, "extras/policy/safety.html", {"pageName": pageName})

def termsView(request):
    pageName = "Terms"
    return render(request, "extras/policy/terms.html", {"pageName": pageName})



def collegeCampusesView(request):
    pageName = "Colleges"
    return render(request, "extras/resources/collegeCampuses.html", {"pageName": pageName})

def affiliateView(request):
    pageName = "Affiliate"
    return render(request, "extras/resources/affiliate.html", {"pageName": pageName})

def partnersView(request):
    pageName = "Partnership"
    return render(request, "extras/resources/partners.html", {"pageName": pageName})