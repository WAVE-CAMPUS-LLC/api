from django.shortcuts import render,redirect, HttpResponse
from django.contrib.auth.decorators import login_required

from supportCenterApp.models import SupportTicket
from wave_v1.decorators import admin_required

# Create your views here.
@login_required(login_url="authentication:login")
@admin_required
def adminPortalView(request):
    if request.user.is_superuser:
        all_support_tickets = SupportTicket.objects.all()
        
        search_query = request.GET.get('support-ticket-search')
        if search_query:
            all_support_tickets = all_support_tickets.filter(ticket_id__icontains=search_query)
        
        active_support_tickets = all_support_tickets.filter(status="Open")
        inactive_support_tickets = all_support_tickets.filter(status="Closed")
        
        return render(request, "adminDashboardApp/index.html", {'active_tickets': active_support_tickets, 'inactive_tickets': inactive_support_tickets, 'search_query': search_query})
    else:
        return HttpResponse("You are not an admin. ")
    

@login_required(login_url="authentication:login")
@admin_required
def adminDashboardView(request):
    if request.user.is_superuser:
        return render(request, "adminDashboardApp/tabs/dashboard.html")
    
    else:
        return HttpResponse("You are not an admin. ")
    
    
@login_required(login_url="authentication:login")
@admin_required
def adminEventsView(request):
    if request.user.is_superuser:
        return render(request, "adminDashboardApp/tabs/events.html")
    
    else:
        return HttpResponse("You are not an admin. ")
    
    
@login_required(login_url="authentication:login")
@admin_required
def adminUsersView(request):
    if request.user.is_superuser:
        return render(request, "adminDashboardApp/tabs/users.html")
    
    else:
        return HttpResponse("You are not an admin. ")
    
    
@login_required(login_url="authentication:login")
@admin_required
def adminJobsView(request):
    if request.user.is_superuser:
        return render(request, "adminDashboardApp/tabs/jobs.html")
    
    else:
        return HttpResponse("You are not an admin. ")
    
    
@login_required(login_url="authentication:login")
@admin_required
def adminFinanceView(request):
    if request.user.is_superuser:
        return render(request, "adminDashboardApp/tabs/financial.html")
    
    else:
        return HttpResponse("You are not an admin. ")
    
    
@login_required(login_url="authentication:login")
@admin_required
def adminSupportView(request):
    if request.user.is_superuser:
        return render(request, "adminDashboardApp/tabs/support.html")
    
    else:
        return HttpResponse("You are not an admin. ")
    
    
@login_required(login_url="authentication:login")
@admin_required
def adminFeedbackView(request):
    if request.user.is_superuser:
        return render(request, "adminDashboardApp/tabs/feedback.html")
    
    else:
        return HttpResponse("You are not an admin. ")