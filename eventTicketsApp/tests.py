from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Ticket, PaidFreeTicket, RSVPTicket
from eventManagementApp.models import Event

class TicketPurchaseTests(TestCase):

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

    def test_ticket_purchase(self):
        response = self.client.post(reverse('eventTickets:checkout'), {
            'cart': {
                'ticket1': {
                    'eventId': str(self.event.eventId),
                    'price': '10.00',
                    'quantity': 1
                }
            }
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Ticket.objects.filter(event=self.event, user=self.user).exists())

    def test_payment_processing(self):
        response = self.client.post(reverse('eventTickets:createPaymentIntent'), {
            'cart': {
                'ticket1': {
                    'eventId': str(self.event.eventId),
                    'price': '10.00',
                    'quantity': 1
                }
            },
            'useStoredPaymentMethod': False
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('clientSecret', response.json())

class TicketValidationTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
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
        self.ticket = Ticket.objects.create(
            user=self.user,
            event=self.event,
            guestFirstName='Test',
            guestLastName='User',
            guestEmail='testuser@example.com'
        )

    def test_ticket_validation(self):
        response = self.client.post(reverse('eventTickets:verifyTicket'), {
            'ticketId': str(self.ticket.ticketId),
            'eventId': str(self.event.eventId),
            'status': 'Valid'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['valid'], True)

    def test_ticket_scanning(self):
        self.ticket.status = 'Scanned'
        self.ticket.save()
        response = self.client.post(reverse('eventTickets:verifyTicket'), {
            'ticketId': str(self.ticket.ticketId),
            'eventId': str(self.event.eventId),
            'status': 'Scanned'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['valid'], False)

class TicketRefundTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
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
        self.ticket = Ticket.objects.create(
            user=self.user,
            event=self.event,
            guestFirstName='Test',
            guestLastName='User',
            guestEmail='testuser@example.com'
        )

    def test_ticket_refund(self):
        response = self.client.post(reverse('eventTickets:paymentFailed'), {
            'ticketId': str(self.ticket.ticketId),
            'eventId': str(self.event.eventId)
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['message'], 'Refund processed successfully')
