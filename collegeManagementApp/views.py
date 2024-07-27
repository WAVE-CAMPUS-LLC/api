from django.shortcuts import get_object_or_404, render, redirect
from .forms import CollegeForm
from .models import College


# Create your views here.
def collegeHomeView(request):
    pageName = "Colleges"
    return render(request, "collegeManagementApp/home.html", {"pageName": pageName})


def collegeCampusesView(request):
    pageName = "Colleges"

    colleges = College.objects.all()
    return render(
        request,
        "collegeManagementApp/campuses.html",
        {"pageName": pageName, "colleges": colleges},
    )


def addCollegeView(request):
    pageName = "Colleges"

    if request.method == "POST":
        collegeForm = CollegeForm(request.POST, request.FILES)

        if collegeForm.is_valid():
            collegeForm.save()

            return redirect("colleges:find")
    else:
        collegeForm = CollegeForm()
    return render(
        request,
        "collegeManagementApp/add.html",
        {"pageName": pageName, "collegeForm": collegeForm},
    )


def viewCollegeInformation(request, collegeId):
    pageName = "Colleges"

    college = get_object_or_404(College, collegeId=collegeId)
    
    return render(
        request, "collegeManagementApp/collegeInformation.html", {"pageName": pageName, "college":college}
    )
