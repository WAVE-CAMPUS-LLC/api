from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Visitor
from eventManagementApp.models import Event
from accountManagementApp.models import UserProfile

class CoreFunctionalityTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.user_profile = UserProfile.objects.create(user=self.user)
        self.event = Event.objects.create(
            title='Test Event',
            description='This is a test event.',
            date='2023-01-01',
            time='12:00',
            location='Test Location',
            host=self.user
        )

    def test_notifications(self):
        response = self.client.get(reverse('core:explore'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'coreApp/explore.html')

    def test_messaging(self):
        response = self.client.get(reverse('core:eventDetails', args=[self.event.eventId]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'coreApp/event/eventDetails.html')

    def test_user_activity_tracking(self):
        response = self.client.get(reverse('core:trackVisitor'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ip_address')

    def test_system_settings_and_configurations(self):
        response = self.client.get(reverse('core:categories'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'coreApp/categories.html')

class VisitorTests(TestCase):

    def setUp(self):
        self.client = Client()

    def test_visitor_creation(self):
        response = self.client.get(reverse('core:trackVisitor'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Visitor.objects.exists())

    def test_visitor_ip_address(self):
        response = self.client.get(reverse('core:trackVisitor'))
        self.assertEqual(response.status_code, 200)
        visitor = Visitor.objects.first()
        self.assertIsNotNone(visitor.ip_address)

    def test_visitor_first_visit(self):
        response = self.client.get(reverse('core:trackVisitor'))
        self.assertEqual(response.status_code, 200)
        visitor = Visitor.objects.first()
        self.assertIsNotNone(visitor.first_visit)
