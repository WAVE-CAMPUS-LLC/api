from django.shortcuts import render, redirect
from .forms import JoinForm
# from django.http import HttpResponse

# Create your views here.
def joinView(request):
    if request.method == 'POST':
        form = JoinForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('accountManagement:userAccount')
    else:
        form = JoinForm()
    return render(request, 'authenticationApp/join.html', {'form': form})


def loginView(request):
    return render(request, 'authenticationApp/login.html')