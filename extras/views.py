from django.shortcuts import render, redirect

# Create your views here.


def aboutView(request):
    pageName = "About"
    return render(request, "extras/company/about.html", {"pageName": pageName})


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


def affiliateView(request):
    pageName = "Affiliate"
    return render(request, "extras/resources/affiliate.html", {"pageName": pageName})

def partnersView(request):
    pageName = "Partnership"
    return render(request, "extras/resources/partners.html", {"pageName": pageName})


def error_404(request, exception):
    return render(request, 'extras/invalid/invalid.html', status=404)