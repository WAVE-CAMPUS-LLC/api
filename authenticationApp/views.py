from django.shortcuts import render, redirect
from .forms import CustomUserJoinForm, UserAuthenticationForm
from django.contrib.auth import login, logout, authenticate
from .models import CustomUser
# from django.http import HttpResponse

# Create your views here.
def joinView(request):
    if request.method == 'POST':
        form = CustomUserJoinForm(request.POST)
        if form.is_valid():
            print("Form is valid!")
            user = form.save()
            login(request, user)
            return redirect("accountManagement:userAccount")
        else:
            print(form.errors)
    else:
        form = CustomUserJoinForm()
    return render(request, 'authenticationApp/join.html', {'form': form})


def loginView(request):
    if request.method == "POST":
        form = UserAuthenticationForm(data=request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)
            
            if user is not None:
                login(request, user)
                return redirect("accountManagement:userAccount")
            else:
                form.add_error(None, 'Invalid email or password')
    else:
        form = UserAuthenticationForm()
    return render(request, 'authenticationApp/login.html', {'form': form})

def logoutView(request):
    logout(request)
    return redirect("core:index")