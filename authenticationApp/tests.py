from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.core import mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from .models import EmailVerification

User = get_user_model()

class UsersManagersTests(TestCase):

    def test_create_user(self):
        user = User.objects.create_user(email="normal@user.com", password="foo")
        self.assertEqual(user.email, "normal@user.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        try:
            self.assertIsNone(user.username)
        except AttributeError:
            pass
        with self.assertRaises(TypeError):
            User.objects.create_user()
        with self.assertRaises(TypeError):
            User.objects.create_user(email="normal@user.com")
        with self.assertRaises(ValueError):
            User.objects.create_user(email="normal@user.com", password="foo")

    def test_create_superuser(self):
        admin_user = User.objects.create_superuser(email="super@user.com", password="foo")
        self.assertEqual(admin_user.email, "super@user.com")
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        try:
            self.assertIsNone(admin_user.username)
        except AttributeError:
            pass
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="super@user.com", password="foo", is_superuser=False)

class UserRegistrationAndLoginTests(TestCase):

    def setUp(self):
        self.user_data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "testuser@example.com",
            "username": "testuser",
            "birthday": "2000-01-01",
            "password1": "password123",
            "password2": "password123",
        }

    def test_user_registration(self):
        response = self.client.post(reverse("authentication:join"), self.user_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email="testuser@example.com").exists())

    def test_user_login(self):
        User.objects.create_user(email="testuser@example.com", password="password123")
        response = self.client.post(reverse("authentication:login"), {
            "identifier": "testuser@example.com",
            "password": "password123",
        })
        self.assertEqual(response.status_code, 302)

class PasswordResetAndEmailVerificationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="testuser@example.com", password="password123")

    def test_password_reset(self):
        response = self.client.post(reverse("authentication:forgot"), {"email": "testuser@example.com"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset", mail.outbox[0].subject)

    def test_email_verification(self):
        verification_code = "123456"
        EmailVerification.objects.create(user=self.user, verification_code=verification_code, expiration_date=timezone.now() + timezone.timedelta(hours=12))
        self.client.login(email="testuser@example.com", password="password123")
        response = self.client.post(reverse("authentication:verifyEmail"), {"action": "verifyEmailCode", "verification_code": verification_code})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)

class UserRolesAndPermissionsTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="testuser@example.com", password="password123")

    def test_user_roles(self):
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_user_permissions(self):
        self.assertTrue(self.user.has_perm("authenticationApp.view_profile_overview"))
        self.assertFalse(self.user.has_perm("authenticationApp.manage_users"))
