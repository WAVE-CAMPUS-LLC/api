from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from dataAnalyticsAPI.models import InteractiveEventControl, GuestUser
from eventManagementApp.models import Event
from authenticationApp.models import CustomUser
import json

User = get_user_model()

class DataAnalyticsAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.event = Event.objects.create(
            title='Test Event',
            description='This is a test event.',
            date='2023-01-01',
            time='12:00',
            location='Test Location',
            host=self.user
        )

    def test_track_event_clicks_authenticated_user(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('analyticsAPI:trackEventClicks'), json.dumps({'event_id': str(self.event.eventId)}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(InteractiveEventControl.objects.filter(event=self.event, user=self.user, interaction_type='Clicked').exists())

    def test_track_event_clicks_guest_user(self):
        response = self.client.post(reverse('analyticsAPI:trackEventClicks'), json.dumps({'event_id': str(self.event.eventId)}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(InteractiveEventControl.objects.filter(event=self.event, guest__isnull=False, interaction_type='Clicked').exists())

    def test_track_event_views_authenticated_user(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('analyticsAPI:trackEventViews'), json.dumps({'event_id': str(self.event.eventId), 'duration': 120}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(InteractiveEventControl.objects.filter(event=self.event, user=self.user, interaction_type='Viewed', duration=120).exists())

    def test_track_event_views_guest_user(self):
        response = self.client.post(reverse('analyticsAPI:trackEventViews'), json.dumps({'event_id': str(self.event.eventId), 'duration': 120}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(InteractiveEventControl.objects.filter(event=self.event, guest__isnull=False, interaction_type='Viewed', duration=120).exists())

    def test_user_signups_daily(self):
        response = self.client.get(reverse('analyticsAPI:userSignups'), {'period': 'daily'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('labels', response.json())
        self.assertIn('counts', response.json())

    def test_user_signups_weekly(self):
        response = self.client.get(reverse('analyticsAPI:userSignups'), {'period': 'weekly'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('labels', response.json())
        self.assertIn('counts', response.json())

    def test_user_signups_monthly(self):
        response = self.client.get(reverse('analyticsAPI:userSignups'), {'period': 'monthly'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('labels', response.json())
        self.assertIn('counts', response.json())

    def test_user_logins_general(self):
        response = self.client.get(reverse('analyticsAPI:userLogins'), {'trend': 'general'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_logins', response.json())
        self.assertIn('unique_users', response.json())
        self.assertIn('active_sessions', response.json())
        self.assertIn('average_session_duration', response.json())

    def test_user_logins_user_activity(self):
        response = self.client.get(reverse('analyticsAPI:userLogins'), {'trend': 'user_activity'})
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_user_logins_time_trends(self):
        response = self.client.get(reverse('analyticsAPI:userLogins'), {'trend': 'time_trends', 'time_frame': 'daily'})
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_user_logins_ip_insights(self):
        response = self.client.get(reverse('analyticsAPI:userLogins'), {'trend': 'ip_insights'})
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_user_logins_security(self):
        response = self.client.get(reverse('analyticsAPI:userLogins'), {'trend': 'security'})
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), dict)

    def test_user_logins_retention(self):
        response = self.client.get(reverse('analyticsAPI:userLogins'), {'trend': 'retention'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('last_7_days', response.json())
        self.assertIn('last_30_days', response.json())

    def test_user_demographics(self):
        response = self.client.get(reverse('analyticsAPI:userDemographics'), {'group_by': 'home_state'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('labels', response.json())
        self.assertIn('counts', response.json())

    def test_college_overview(self):
        response = self.client.get(reverse('analyticsAPI:collegeOverview'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('colleges_by_state', response.json())
        self.assertIn('colleges_by_city', response.json())

    def test_college_membership(self):
        response = self.client.get(reverse('analyticsAPI:collegeMembership'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('members_by_college', response.json())

    def test_organization_overview(self):
        response = self.client.get(reverse('analyticsAPI:organizationOverview'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('organizations_by_college_privacy', response.json())
        self.assertIn('organizations_by_privacy', response.json())

    def test_organization_membership(self):
        response = self.client.get(reverse('analyticsAPI:organizationMembership'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_memberships', response.json())
        self.assertIn('churn_rate', response.json())
        self.assertIn('privacy_comparison', response.json())
        self.assertIn('college_comparison', response.json())
        self.assertIn('organization_sizes', response.json())
        self.assertIn('top_organizations', response.json())
        self.assertIn('active_colleges', response.json())
        self.assertIn('user_membership_distribution', response.json())
        self.assertIn('repeat_memberships', response.json())
        self.assertIn('membership_trends', response.json())
