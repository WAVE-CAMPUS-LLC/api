from django.shortcuts import get_object_or_404, render, redirect
from .forms import CareerRoleApplicationForm
from adminDashboardApp.models import CareerRole, Department

# Create your views here.
def careerHomeApp(request):
    pageName = "Careers"
    
    career_Roles = CareerRole.objects.all()
    
    department_roles = {}
    for role in career_Roles:
        department = role.department
        if department not in department_roles:
            department_roles[department] = []
        department_roles[department].append(role)
        
    
    return render(request, "careerApp/careers.html", {"pageName": pageName, "department_roles": department_roles})

def careerJobDetails(request, roleID):
    career_role = CareerRole.objects.get(roleID=roleID)
    
    if request.method == "POST":
        careerApp = CareerRoleApplicationForm(request.POST)
        if careerApp.is_valid():
            print(f'Applied for the role.')
            careerApp.save()
            return redirect("careers:home")
    else:
        careerApp = CareerRoleApplicationForm()
    return render(request, "careerApp/careerJobDetails.html", {'careerRole':career_role,'careerAppForm': careerApp})