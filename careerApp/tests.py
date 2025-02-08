from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from adminDashboardApp.models import CareerRole, Department
from .models import CareerRoleApplication

class JobPostingTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.department = Department.objects.create(
            name="Engineering",
            lead_name="John Doe",
            lead_email="john.doe@example.com",
            capacity=10,
            location="Building A",
            description="Engineering Department"
        )
        self.career_role = CareerRole.objects.create(
            department=self.department,
            roleTitle="Software Engineer",
            roleDescription="Develop software applications.",
            roleExpectations="Write clean code.",
            roleRequirements="Experience with Python.",
            roleLocation="Remote",
            roleType="Remote",
            advertisementLength=30,
            advertisementStartDate="2023-01-01",
            roleCapacity="Full-Time"
        )

    def test_job_posting_creation(self):
        self.assertEqual(self.career_role.roleTitle, "Software Engineer")
        self.assertEqual(self.career_role.roleDescription, "Develop software applications.")

    def test_job_posting_update(self):
        self.career_role.roleTitle = "Senior Software Engineer"
        self.career_role.save()
        self.assertEqual(self.career_role.roleTitle, "Senior Software Engineer")

    def test_job_posting_deletion(self):
        self.career_role.delete()
        self.assertFalse(CareerRole.objects.filter(roleTitle="Software Engineer").exists())

class JobApplicationTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.department = Department.objects.create(
            name="Engineering",
            lead_name="John Doe",
            lead_email="john.doe@example.com",
            capacity=10,
            location="Building A",
            description="Engineering Department"
        )
        self.career_role = CareerRole.objects.create(
            department=self.department,
            roleTitle="Software Engineer",
            roleDescription="Develop software applications.",
            roleExpectations="Write clean code.",
            roleRequirements="Experience with Python.",
            roleLocation="Remote",
            roleType="Remote",
            advertisementLength=30,
            advertisementStartDate="2023-01-01",
            roleCapacity="Full-Time"
        )

    def test_job_application_submission(self):
        response = self.client.post(reverse('careers:roleDetails', args=[self.career_role.roleID]), {
            'applicantFirstName': 'Jane',
            'applicantLastName': 'Doe',
            'applicantEmail': 'jane.doe@example.com',
            'applicantPhone': '1234567890',
            'applicantGithub': 'https://github.com/janedoe',
            'applicantPortfolio': 'https://janedoe.com',
            'applicantLinkedIn': 'https://linkedin.com/in/janedoe',
            'applicantResume': '',
            'applicantLocation': 'USA',
            'applicantCoverLetter': '',
            'whatYouBring': 'Experience in software development.',
            'workAuthorization': 'Yes'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CareerRoleApplication.objects.filter(applicantEmail='jane.doe@example.com').exists())

    def test_job_application_status_update(self):
        application = CareerRoleApplication.objects.create(
            role=self.career_role,
            applicantFirstName='Jane',
            applicantLastName='Doe',
            applicantEmail='jane.doe@example.com',
            applicantPhone='1234567890',
            applicantGithub='https://github.com/janedoe',
            applicantPortfolio='https://janedoe.com',
            applicantLinkedIn='https://linkedin.com/in/janedoe',
            applicantResume='',
            applicantLocation='USA',
            applicantCoverLetter='',
            whatYouBring='Experience in software development.',
            workAuthorization='Yes'
        )
        application.approval_status = 'approved'
        application.save()
        self.assertEqual(application.approval_status, 'approved')

class JobSearchTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.department = Department.objects.create(
            name="Engineering",
            lead_name="John Doe",
            lead_email="john.doe@example.com",
            capacity=10,
            location="Building A",
            description="Engineering Department"
        )
        self.career_role = CareerRole.objects.create(
            department=self.department,
            roleTitle="Software Engineer",
            roleDescription="Develop software applications.",
            roleExpectations="Write clean code.",
            roleRequirements="Experience with Python.",
            roleLocation="Remote",
            roleType="Remote",
            advertisementLength=30,
            advertisementStartDate="2023-01-01",
            roleCapacity="Full-Time"
        )

    def test_job_search(self):
        response = self.client.get(reverse('careers:home'), {'search': 'Software Engineer'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Software Engineer')

    def test_job_filtering(self):
        response = self.client.get(reverse('careers:home'), {'filter': 'Engineering'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Software Engineer')
