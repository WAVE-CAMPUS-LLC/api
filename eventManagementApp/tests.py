from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Event, HostApplication, EventType
from eventTicketsApp.models import RSVPTicket, PaidFreeTicket, InviteEventOption

class EventCreationTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.login(username='testuser', password='password123')

    def test_event_creation(self):
        response = self.client.post(reverse('eventManagement:createRsvpEvent'), {
            'title': 'Test Event',
            'event_type': 'Social',
            'date': '2023-01-01',
            'start_time': '12:00',
            'end_time': '14:00',
            'description': 'This is a test event.',
            'privacy': 'Discoverable',
            'country': 'United States',
            'building_name': 'Test Building',
            'street': '123 Test St',
            'city': 'Test City',
            'state': 'CA',
            'zip_code': '12345'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Event.objects.filter(title='Test Event').exists())

    def test_event_update(self):
        event = Event.objects.create(
            title='Test Event',
            event_type='Social',
            date='2023-01-01',
            start_time='12:00',
            end_time='14:00',
            description='This is a test event.',
            privacy='Discoverable',
            country='United States',
            building_name='Test Building',
            street='123 Test St',
            city='Test City',
            state='CA',
            zip_code='12345',
            host=self.user
        )
        response = self.client.post(reverse('eventManagement:editEvent', args=[event.eventId]), {
            'title': 'Updated Event',
            'event_type': 'Social',
            'date': '2023-01-01',
            'start_time': '12:00',
            'end_time': '14:00',
            'description': 'This is an updated test event.',
            'privacy': 'Discoverable',
            'country': 'United States',
            'building_name': 'Test Building',
            'street': '123 Test St',
            'city': 'Test City',
            'state': 'CA',
            'zip_code': '12345'
        })
        self.assertEqual(response.status_code, 302)
        event.refresh_from_db()
        self.assertEqual(event.title, 'Updated Event')

    def test_event_deletion(self):
        event = Event.objects.create(
            title='Test Event',
            event_type='Social',
            date='2023-01-01',
            start_time='12:00',
            end_time='14:00',
            description='This is a test event.',
            privacy='Discoverable',
            country='United States',
            building_name='Test Building',
            street='123 Test St',
            city='Test City',
            state='CA',
            zip_code='12345',
            host=self.user
        )
        response = self.client.post(reverse('eventManagement:eventManagement', args=[event.eventId]), {
            'eventAction': 'deleteEvent'
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Event.objects.filter(title='Test Event').exists())

class EventTicketingTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.login(username='testuser', password='password123')
        self.event = Event.objects.create(
            title='Test Event',
            event_type='Social',
            date='2023-01-01',
            start_time='12:00',
            end_time='14:00',
            description='This is a test event.',
            privacy='Discoverable',
            country='United States',
            building_name='Test Building',
            street='123 Test St',
            city='Test City',
            state='CA',
            zip_code='12345',
            host=self.user
        )

    def test_rsvp_ticket_creation(self):
        response = self.client.post(reverse('eventManagement:createRsvpEvent'), {
            'title': 'Test Event',
            'event_type': 'Social',
            'date': '2023-01-01',
            'start_time': '12:00',
            'end_time': '14:00',
            'description': 'This is a test event.',
            'privacy': 'Discoverable',
            'country': 'United States',
            'building_name': 'Test Building',
            'street': '123 Test St',
            'city': 'Test City',
            'state': 'CA',
            'zip_code': '12345'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(RSVPTicket.objects.filter(event=self.event).exists())

    def test_paid_ticket_creation(self):
        response = self.client.post(reverse('eventManagement:createPaidEvent'), {
            'title': 'Test Event',
            'event_type': 'Social',
            'date': '2023-01-01',
            'start_time': '12:00',
            'end_time': '14:00',
            'description': 'This is a test event.',
            'privacy': 'Discoverable',
            'country': 'United States',
            'building_name': 'Test Building',
            'street': '123 Test St',
            'city': 'Test City',
            'state': 'CA',
            'zip_code': '12345'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(PaidFreeTicket.objects.filter(event=self.event).exists())

    def test_invite_ticket_creation(self):
        response = self.client.post(reverse('eventManagement:createInviteEvent'), {
            'title': 'Test Event',
            'event_type': 'Social',
            'date': '2023-01-01',
            'start_time': '12:00',
            'end_time': '14:00',
            'description': 'This is a test event.',
            'privacy': 'Discoverable',
            'country': 'United States',
            'building_name': 'Test Building',
            'street': '123 Test St',
            'city': 'Test City',
            'state': 'CA',
            'zip_code': '12345'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(InviteEventOption.objects.filter(event=self.event).exists())

class EventNotificationTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.login(username='testuser', password='password123')
        self.event = Event.objects.create(
            title='Test Event',
            event_type='Social',
            date='2023-01-01',
            start_time='12:00',
            end_time='14:00',
            description='This is a test event.',
            privacy='Discoverable',
            country='United States',
            building_name='Test Building',
            street='123 Test St',
            city='Test City',
            state='CA',
            zip_code='12345',
            host=self.user
        )

    def test_event_notifications(self):
        response = self.client.post(reverse('eventManagement:eventManagement', args=[self.event.eventId]), {
            'eventAction': 'sendInvites',
            'invite_emails': 'invitee@example.com',
            'invite_subject': 'Test Event Invitation',
            'invite_message': 'You are invited to Test Event.'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(InviteEventOption.objects.filter(event=self.event, email='invitee@example.com').exists())

    def test_event_reminders(self):
        response = self.client.post(reverse('eventManagement:eventManagement', args=[self.event.eventId]), {
            'eventAction': 'sendReminders',
            'reminder_emails': 'reminder@example.com',
            'reminder_subject': 'Test Event Reminder',
            'reminder_message': 'This is a reminder for Test Event.'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(InviteEventOption.objects.filter(event=self.event, email='reminder@example.com').exists())
