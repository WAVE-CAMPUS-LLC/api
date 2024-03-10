from django.utils import timezone
from django.shortcuts import render, redirect
from .forms import CustomUserJoinForm, UserAuthenticationForm
from django.contrib.auth import login, logout, authenticate
from .models import CustomUser
from adminDashboardApp.models import LoginHistoryModel
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
                login_history = LoginHistoryModel.objects.create(user=user, email=user.email, ip_address=request.META.get('REMOTE_ADDR'))
                login_history.save()
                return redirect("accountManagement:userAccount")
            else:
                form.add_error(None, 'Invalid email or password')
    else:
        form = UserAuthenticationForm()
    return render(request, 'authenticationApp/login.html', {'form': form})

def logoutView(request):
    try:
        login_history = LoginHistoryModel.objects.filter(user=request.user).latest('login_time')
        login_history.end_session()
    except LoginHistoryModel.DoesNotExist:
        pass
    
    logout(request)
    return redirect("core:index")

def forgotPasswordView(request):
    return render(request, 'authenticationApp/forgot_password.html')