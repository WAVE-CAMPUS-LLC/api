from django.db import models
from adminDashboardApp.models import Department, CareerRole


class CareerRoleApplication(models.Model):
    role = models.ForeignKey(CareerRole, on_delete=models.CASCADE)
    applicantFirstName = models.CharField(verbose_name="First Name",max_length=70)
    applicantLastName = models.CharField(verbose_name="Last Name", max_length=70)
    applicantEmail = models.EmailField(verbose_name="Email")
    applicantPhone = models.CharField(verbose_name="Phone", max_length=10)
    applicantGithub = models.URLField(verbose_name="GitHub")
    applicantPortfolio = models.URLField(verbose_name="Portfolio")
    applicantLinkedIn = models.URLField(verbose_name="LinkedIn Profile")
    applicantResume = models.FileField(verbose_name="Resume",upload_to='resumes/', blank=True, null=True)
    applicantLocation = models.CharField(verbose_name="Location (Country, State/Region)", max_length=100)
    applicantCoverLetter = models.FileField(verbose_name="Cover Letter", upload_to='coverLetters/', blank=True, null=True)
    whatYouBring = models.TextField(verbose_name="What do you bring to the team?")
    workAuthorization = models.TextField(verbose_name="Are you legally authorized to work for us?")
    
    
    def __str__(self):
        return f'{self.applicantFirstName} {self.applicantLastName} applied for {self.role.roleTitle}'