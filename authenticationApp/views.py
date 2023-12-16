from django.shortcuts import render
# from django.http import HttpResponse

# Create your views here.
def joinView(request):
    return render(request, 'authenticationApp/join.html')


def loginView(request):
    return render(request, 'authenticationApp/login.html')