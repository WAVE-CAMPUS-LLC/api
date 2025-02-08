from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from accountManagementApp.models import UserProfile
from .models import FriendRequest, Crew, CrewMember, CrewRequest

class SocialProfileTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.user_profile = UserProfile.objects.create(user=self.user)

    def test_social_profile_creation(self):
        self.assertEqual(self.user_profile.user.username, 'testuser')
        self.assertEqual(self.user_profile.user.email, 'testuser@example.com')

    def test_social_profile_update(self):
        self.user_profile.bio = "Updated bio"
        self.user_profile.save()
        self.assertEqual(self.user_profile.bio, "Updated bio")

    def test_social_profile_deletion(self):
        self.user_profile.delete()
        self.assertFalse(UserProfile.objects.filter(user=self.user).exists())

class SocialConnectionsTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')
        self.user1_profile = UserProfile.objects.create(user=self.user1)
        self.user2_profile = UserProfile.objects.create(user=self.user2)

    def test_send_friend_request(self):
        friend_request = FriendRequest.objects.create(sender=self.user1, receiver=self.user2)
        self.assertEqual(friend_request.status, 'pending')

    def test_accept_friend_request(self):
        friend_request = FriendRequest.objects.create(sender=self.user1, receiver=self.user2)
        friend_request.accept_request()
        self.assertEqual(friend_request.status, 'accepted')

    def test_decline_friend_request(self):
        friend_request = FriendRequest.objects.create(sender=self.user1, receiver=self.user2)
        friend_request.decline_request()
        self.assertEqual(friend_request.status, 'declined')

    def test_cancel_friend_request(self):
        friend_request = FriendRequest.objects.create(sender=self.user1, receiver=self.user2)
        friend_request.delete()
        self.assertFalse(FriendRequest.objects.filter(sender=self.user1, receiver=self.user2).exists())

class SocialActivityTrackingTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.user_profile = UserProfile.objects.create(user=self.user)
        self.crew = Crew.objects.create(name="Test Crew", created_by=self.user)
        self.crew_member = CrewMember.objects.create(user=self.user, crew=self.crew, is_admin=True)

    def test_crew_creation(self):
        self.assertEqual(self.crew.name, "Test Crew")
        self.assertEqual(self.crew.created_by.username, 'testuser')

    def test_crew_member_addition(self):
        self.assertTrue(CrewMember.objects.filter(user=self.user, crew=self.crew).exists())

    def test_crew_member_removal(self):
        self.crew_member.delete()
        self.assertFalse(CrewMember.objects.filter(user=self.user, crew=self.crew).exists())

    def test_crew_request_creation(self):
        crew_request = CrewRequest.objects.create(sender=self.user, receiver=self.user, crew=self.crew)
        self.assertEqual(crew_request.status, 'pending')

    def test_crew_request_acceptance(self):
        crew_request = CrewRequest.objects.create(sender=self.user, receiver=self.user, crew=self.crew)
        crew_request.accept_request()
        self.assertEqual(crew_request.status, 'accepted')

    def test_crew_request_decline(self):
        crew_request = CrewRequest.objects.create(sender=self.user, receiver=self.user, crew=self.crew)
        crew_request.decline_request()
        self.assertEqual(crew_request.status, 'declined')
