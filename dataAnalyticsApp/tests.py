from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from dataAnalyticsApp.models import UserAnalytics, DataFilter, DataSegment

class DataAnalyticsDashboardTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.login(username='testuser', password='password123')

    def test_dashboard_view(self):
        response = self.client.get(reverse('dataAnalytics:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dataAnalyticsApp/home.html')

    def test_user_data_analytics(self):
        response = self.client.get(reverse('dataAnalytics:userSignups'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dataAnalyticsApp/userAnalytics/userSignups.html')

        response = self.client.get(reverse('dataAnalytics:userLogins'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dataAnalyticsApp/userAnalytics/userLogins.html')

        response = self.client.get(reverse('dataAnalytics:userDemographics'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dataAnalyticsApp/userAnalytics/userDemographics.html')

    def test_data_filtering(self):
        data_filter = DataFilter.objects.create(name='Test Filter', filter_type='age', filter_value='18-25')
        response = self.client.get(reverse('dataAnalytics:home'), {'filter': data_filter.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Filter')

    def test_data_segmentation(self):
        data_segment = DataSegment.objects.create(name='Test Segment', segment_type='location', segment_value='USA')
        response = self.client.get(reverse('dataAnalytics:home'), {'segment': data_segment.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Segment')
