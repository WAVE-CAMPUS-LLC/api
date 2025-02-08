from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import UserProfile, EventTypePreferences
from .forms import UpdateProfilePhotoForm, UpdateContactInfo, UpdatePersonalInfo

User = get_user_model()

class UserProfileTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', email='testuser@example.com', password='password123'
        )
        self.profile = UserProfile.objects.create(user=self.user)

    def test_user_profile_creation(self):
        self.assertEqual(self.profile.user.username, 'testuser')
        self.assertEqual(self.profile.user.email, 'testuser@example.com')

    def test_user_profile_update(self):
        self.profile.is_campus_manager = True
        self.profile.save()
        self.assertTrue(self.profile.is_campus_manager)

    def test_user_profile_deletion(self):
        self.profile.delete()
        self.assertFalse(UserProfile.objects.filter(user=self.user).exists())

class UserPreferencesTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', email='testuser@example.com', password='password123'
        )
        self.profile = UserProfile.objects.create(user=self.user)

    def test_update_profile_photo(self):
        form_data = {'profile_photo': 'path/to/photo.jpg'}
        form = UpdateProfilePhotoForm(data=form_data, instance=self.profile)
        self.assertTrue(form.is_valid())

    def test_update_contact_info(self):
        form_data = {'email': 'newemail@example.com', 'phone_number': '1234567890'}
        form = UpdateContactInfo(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())

    def test_update_personal_info(self):
        form_data = {'first_name': 'New', 'last_name': 'Name'}
        form = UpdatePersonalInfo(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())

class UserAuthenticationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', email='testuser@example.com', password='password123'
        )

    def test_user_login(self):
        login = self.client.login(username='testuser', password='password123')
        self.assertTrue(login)

    def test_user_logout(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('authentication:logout'))
        self.assertEqual(response.status_code, 302)  # Redirect after logout

    def test_user_authorization(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('accountManagement:userAccount'))
        self.assertEqual(response.status_code, 200)
