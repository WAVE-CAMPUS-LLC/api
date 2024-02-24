from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from .forms import SupportTicketForm
from .models import SupportTicket



# Create your views here.
def mainSupportView(request):
    return render(request, "supportCenterApp/support.html")


@login_required(login_url="authentication:login")
def supportPortal(request):
    user_tickets = SupportTicket.objects.filter(user=request.user)
    
    current_tickets = user_tickets.filter(status="Open")
    previous_tickets = user_tickets.filter(status="Closed")
    
    if user_tickets.exists():
        return render(request, 'supportCenterApp/portal/support_portal_with_tickets.html', {'current_tickets': current_tickets, 'previous_tickets': previous_tickets,})
    else:
        return render(request, 'supportCenterApp/portal/support_portal_without_ticket.html')


@login_required(login_url="authentication:login")
def supportTicket(request):
    if request.method == "POST":
        form = SupportTicketForm(request.POST)
        if form.is_valid():
            support_ticket = form.save(commit=False)
            support_ticket.user = request.user
            support_ticket.save()
            return redirect("support:supportPortal")
    else:
        form = SupportTicketForm()
    return render(request, "supportCenterApp/ticket/createTicket.html", {'form': form})


def userFeedback(request):
    return render(request, "supportCenterApp/feedback/provideFeedback.html")