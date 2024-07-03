from django.shortcuts import redirect, render
from .forms import HostApplicationForm
from .models import EventType, HostApplication

# Create your views here.
def hostView(request):
    pageName = "Host Event"
    return render(request, "eventManagementApp/host/hostHome.html", {"pageName": pageName})


def hostApplyView(request):
    """
    The `hostApplyView` function handles the submission of a host application form in a Django web
    application.
    
    :param request: The `request` parameter in the `hostApplyView` function is an object that contains
    information about the current HTTP request. It includes details such as the request method (GET,
    POST, etc.), request data (POST data, query parameters), user session information, and more. In this
    function,
    :return: The `hostApplyView` function returns a rendered HTML template named "hostApplication.html"
    along with a form object. The form object is either a new instance of `HostApplicationForm` if the
    request method is not POST, or a form populated with the POST data if the request method is POST and
    the form is valid. If the form is valid, the function also saves the form data to
    """
    if request.method == "POST":
        form = HostApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.save()
            event_types = form.cleaned_data['eventTypes']
            event_type_objs = [EventType.objects.get_or_create(name=et)[0] for et in event_types]
            application.eventTypes.set(event_type_objs)
            return redirect("eventManagement:hostHome")
    else:
        form = HostApplicationForm()
    return render(request, "eventManagementApp/host/hostApplication.html", {'form': form})


def hostPortalView(request):
    return render(request, "eventManagementApp/host/hostPortal.html")


def hostGuideView(request):
    return render(request, "eventManagementApp/host/hostGuide.html")