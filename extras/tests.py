from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import FAQ, UserFeedback, SystemNotification

class FAQTests(TestCase):

    def setUp(self):
        self.client = Client()

    def test_faq_page(self):
        response = self.client.get(reverse('extras:faq'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'extras/policy/faq.html')

    def test_faq_content(self):
        FAQ.objects.create(question="What is this?", answer="This is a test.")
        response = self.client.get(reverse('extras:faq'))
        self.assertContains(response, "What is this?")
        self.assertContains(response, "This is a test.")

class UserFeedbackTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_feedback_submission(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('extras:feedback'), {
            'rating': 5,
            'comments': 'Great website!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UserFeedback.objects.filter(user=self.user, rating=5, comments='Great website!').exists())

    def test_feedback_page(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('extras:feedback'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'extras/feedback.html')

class SystemNotificationTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_system_notification_creation(self):
        notification = SystemNotification.objects.create(
            user=self.user,
            message="This is a test notification.",
            notification_type="info"
        )
        self.assertEqual(notification.message, "This is a test notification.")
        self.assertEqual(notification.notification_type, "info")

    def test_system_notification_display(self):
        SystemNotification.objects.create(
            user=self.user,
            message="This is a test notification.",
            notification_type="info"
        )
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('extras:notifications'))
        self.assertContains(response, "This is a test notification.")
