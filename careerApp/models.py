from django.db import models
from adminDashboardApp.models import Department

# Create your models here.
class CareerRole(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='career_app_career_role')
    roleTitle = models.CharField("Name",max_length=100)
    companyOverview = models.TextField("Company Summary", help_text="Company Summary")
    roleDescription = models.TextField("Description")
    roleExpectations = models.TextField("What's expected")
    roleExperience = models.TextField("What's expected of you")
    
    def __str__(self):
        return self.roleTitle
    
    
class CareerRoleApplication(models.Model):
    role = models.ForeignKey(CareerRole, on_delete=models.CASCADE)
    applicantFirstName = models.CharField(max_length=70)
    applicantLastName = models.CharField(max_length=70)
    applicantEmail = models.EmailField()
    applicantResume = models.FileField(upload_to='resumes/')
    applicantCoverLetter = models.TextField()
    
    def __str__(self):
        return f'{self.applicantFirstName} {self.applicantLastName} applied for {self.role.roleTitle}'