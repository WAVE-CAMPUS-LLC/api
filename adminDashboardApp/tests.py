from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from .models import Department, CareerRole, LoginHistoryModel, Newsroom, College
from .forms import CreateGroupForm, UpdateGroupForm, DepartmentForm, CareerRoleCreationForm, CreateNewsForm, UpdateNewsTitleForm, UpdateNewsBodyForm, UpdateUrgencyLevelForm, UpdateNewsCategoryForm, UpdateHeaderImageForm, UpdateImageOneForm, UpdateImageTwoForm, UpdateImageThreeForm, CollegeForm, EditCollegeForm

class AdminDashboardTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin', password='admin123')
        self.user.is_staff = True
        self.user.save()
        self.client.login(username='admin', password='admin123')

    def test_admin_portal_view(self):
        response = self.client.get(reverse('waveAdmin:adminDashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/index.html')

    def test_admin_dashboard_view(self):
        response = self.client.get(reverse('waveAdmin:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/dashboard.html')

    def test_admin_department_view(self):
        response = self.client.get(reverse('waveAdmin:departments'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/departments.html')

    def test_admin_user_analytics_view(self):
        response = self.client.get(reverse('waveAdmin:userAnalytics'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/analytics/users.html')

    def test_admin_career_applications_view(self):
        response = self.client.get(reverse('waveAdmin:careerApplications'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/applications/careerApplications.html')

    def test_admin_event_hosts_view(self):
        response = self.client.get(reverse('waveAdmin:eventHosts'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/events/hosts.html')

    def test_admin_events_view(self):
        response = self.client.get(reverse('waveAdmin:events'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/events/events.html')

    def test_admin_users_view(self):
        response = self.client.get(reverse('waveAdmin:users'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/users.html')

    def test_admin_roles_view(self):
        response = self.client.get(reverse('waveAdmin:roles'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/roles.html')

    def test_admin_careers_view(self):
        response = self.client.get(reverse('waveAdmin:careers'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/careers.html')

    def test_admin_connected_accounts_view(self):
        response = self.client.get(reverse('waveAdmin:connectedAccounts'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/financial/accounts.html')

    def test_admin_products_view(self):
        response = self.client.get(reverse('waveAdmin:stripeProducts'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/financial/products.html')

    def test_admin_financial_settings_view(self):
        response = self.client.get(reverse('waveAdmin:financialSettings'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/financial/stripeSettings.html')

    def test_admin_support_view(self):
        response = self.client.get(reverse('waveAdmin:support'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/support.html')

    def test_admin_feedback_view(self):
        response = self.client.get(reverse('waveAdmin:feedback'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/feedback.html')

    def test_admin_college_view(self):
        response = self.client.get(reverse('waveAdmin:colleges'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/colleges/colleges.html')

    def test_admin_college_orgs_view(self):
        response = self.client.get(reverse('waveAdmin:organizations'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/colleges/organizations.html')

    def test_admin_newsroom_view(self):
        response = self.client.get(reverse('waveAdmin:newsroom'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/newsroom.html')

    def test_admin_create_news_view(self):
        response = self.client.get(reverse('waveAdmin:createNews'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/newsroom/createNews.html')

    def test_admin_blog_view(self):
        response = self.client.get(reverse('waveAdmin:blog'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/blog.html')

    def test_admin_emailing_view(self):
        response = self.client.get(reverse('waveAdmin:emailing'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/emailing.html')

class UserManagementTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin', password='admin123')
        self.user.is_staff = True
        self.user.save()
        self.client.login(username='admin', password='admin123')

    def test_suspend_user(self):
        user_to_suspend = User.objects.create_user(username='user1', password='user123')
        response = self.client.post(reverse('waveAdmin:user-detailed', args=[user_to_suspend.username]), {'action': 'suspend'})
        self.assertEqual(response.status_code, 302)
        user_to_suspend.refresh_from_db()
        self.assertTrue(user_to_suspend.is_suspended)

    def test_allow_user(self):
        user_to_allow = User.objects.create_user(username='user2', password='user123')
        user_to_allow.is_suspended = True
        user_to_allow.save()
        response = self.client.post(reverse('waveAdmin:user-detailed', args=[user_to_allow.username]), {'action': 'allow'})
        self.assertEqual(response.status_code, 302)
        user_to_allow.refresh_from_db()
        self.assertFalse(user_to_allow.is_suspended)

    def test_add_role_to_user(self):
        user_to_add_role = User.objects.create_user(username='user3', password='user123')
        group = Group.objects.create(name='TestGroup')
        response = self.client.post(reverse('waveAdmin:user-detailed', args=[user_to_add_role.username]), {'group_id': group.id, 'addRole': True})
        self.assertEqual(response.status_code, 302)
        user_to_add_role.refresh_from_db()
        self.assertTrue(user_to_add_role.groups.filter(name='TestGroup').exists())

    def test_remove_role_from_user(self):
        user_to_remove_role = User.objects.create_user(username='user4', password='user123')
        group = Group.objects.create(name='TestGroup')
        user_to_remove_role.groups.add(group)
        response = self.client.post(reverse('waveAdmin:user-detailed', args=[user_to_remove_role.username]), {'group_id': group.id, 'removeRole': True})
        self.assertEqual(response.status_code, 302)
        user_to_remove_role.refresh_from_db()
        self.assertFalse(user_to_remove_role.groups.filter(name='TestGroup').exists())

class AnalyticsAndReportingTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin', password='admin123')
        self.user.is_staff = True
        self.user.save()
        self.client.login(username='admin', password='admin123')

    def test_user_analytics_view(self):
        response = self.client.get(reverse('waveAdmin:userAnalytics'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/analytics/users.html')

    def test_event_analytics_view(self):
        response = self.client.get(reverse('waveAdmin:events'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/events/events.html')

    def test_financial_analytics_view(self):
        response = self.client.get(reverse('waveAdmin:connectedAccounts'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'adminDashboardApp/tabs/financial/accounts.html')
