from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from adminDashboardApp.models import College
from .models import Organization, Membership, OrganizationMembership

class CollegeManagementTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.college = College.objects.create(
            name="Test College",
            address="123 College St",
            city="Test City",
            state="TS",
            zip_code="12345",
            country="USA",
            motto="Test Motto",
            contact_website="https://www.testcollege.edu"
        )
        self.client.login(username='testuser', password='password123')

    def test_college_creation(self):
        self.assertEqual(self.college.name, "Test College")
        self.assertEqual(self.college.city, "Test City")

    def test_college_update(self):
        self.college.name = "Updated College"
        self.college.save()
        self.assertEqual(self.college.name, "Updated College")

    def test_college_deletion(self):
        self.college.delete()
        self.assertFalse(College.objects.filter(name="Test College").exists())

class CollegeDepartmentAndCourseManagementTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.college = College.objects.create(
            name="Test College",
            address="123 College St",
            city="Test City",
            state="TS",
            zip_code="12345",
            country="USA",
            motto="Test Motto",
            contact_website="https://www.testcollege.edu"
        )
        self.client.login(username='testuser', password='password123')

    def test_department_creation(self):
        response = self.client.post(reverse('adminDashboard:createDepartment'), {
            'name': 'Engineering',
            'lead_name': 'John Doe',
            'lead_email': 'john.doe@example.com',
            'capacity': 100,
            'location': 'Building A',
            'description': 'Engineering Department'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Department.objects.filter(name='Engineering').exists())

    def test_course_creation(self):
        department = Department.objects.create(
            name="Engineering",
            lead_name="John Doe",
            lead_email="john.doe@example.com",
            capacity=100,
            location="Building A",
            description="Engineering Department"
        )
        response = self.client.post(reverse('adminDashboard:createCourse'), {
            'department': department.id,
            'course_name': 'Introduction to Engineering',
            'course_code': 'ENG101',
            'course_description': 'Basic engineering principles'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Course.objects.filter(course_name='Introduction to Engineering').exists())

class CollegeEventManagementTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.college = College.objects.create(
            name="Test College",
            address="123 College St",
            city="Test City",
            state="TS",
            zip_code="12345",
            country="USA",
            motto="Test Motto",
            contact_website="https://www.testcollege.edu"
        )
        self.client.login(username='testuser', password='password123')

    def test_event_creation(self):
        response = self.client.post(reverse('eventManagement:createEvent'), {
            'title': 'Test Event',
            'description': 'This is a test event.',
            'date': '2023-01-01',
            'time': '12:00',
            'location': 'Test Location',
            'college': self.college.id
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Event.objects.filter(title='Test Event').exists())

    def test_event_update(self):
        event = Event.objects.create(
            title='Test Event',
            description='This is a test event.',
            date='2023-01-01',
            time='12:00',
            location='Test Location',
            college=self.college
        )
        response = self.client.post(reverse('eventManagement:updateEvent', args=[event.id]), {
            'title': 'Updated Event',
            'description': 'This is an updated test event.',
            'date': '2023-01-01',
            'time': '12:00',
            'location': 'Test Location',
            'college': self.college.id
        })
        self.assertEqual(response.status_code, 302)
        event.refresh_from_db()
        self.assertEqual(event.title, 'Updated Event')

    def test_event_deletion(self):
        event = Event.objects.create(
            title='Test Event',
            description='This is a test event.',
            date='2023-01-01',
            time='12:00',
            location='Test Location',
            college=self.college
        )
        response = self.client.post(reverse('eventManagement:deleteEvent', args=[event.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Event.objects.filter(title='Test Event').exists())
