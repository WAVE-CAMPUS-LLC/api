from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import SupportTicket, SupportTicketMessage

class SupportTicketTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.login(username='testuser', password='password123')

    def test_support_ticket_creation(self):
        response = self.client.post(reverse('support:newTicket'), {
            'title': 'help',
            'email': 'testuser@example.com',
            'subject': 'Test Support Ticket',
            'description': 'This is a test support ticket.'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SupportTicket.objects.filter(subject='Test Support Ticket').exists())

    def test_support_ticket_update(self):
        ticket = SupportTicket.objects.create(
            user=self.user,
            title='help',
            email='testuser@example.com',
            subject='Test Support Ticket',
            description='This is a test support ticket.'
        )
        ticket.subject = 'Updated Support Ticket'
        ticket.save()
        self.assertEqual(ticket.subject, 'Updated Support Ticket')

    def test_support_ticket_resolution(self):
        ticket = SupportTicket.objects.create(
            user=self.user,
            title='help',
            email='testuser@example.com',
            subject='Test Support Ticket',
            description='This is a test support ticket.'
        )
        ticket.status = 'Closed'
        ticket.save()
        self.assertEqual(ticket.status, 'Closed')

class SupportTicketAssignmentTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.login(username='testuser', password='password123')

    def test_support_ticket_assignment(self):
        ticket = SupportTicket.objects.create(
            user=self.user,
            title='help',
            email='testuser@example.com',
            subject='Test Support Ticket',
            description='This is a test support ticket.'
        )
        ticket.assigned_to = self.user
        ticket.save()
        self.assertEqual(ticket.assigned_to, self.user)

    def test_support_ticket_escalation(self):
        ticket = SupportTicket.objects.create(
            user=self.user,
            title='help',
            email='testuser@example.com',
            subject='Test Support Ticket',
            description='This is a test support ticket.'
        )
        ticket.escalated = True
        ticket.save()
        self.assertTrue(ticket.escalated)

class SupportTicketNotificationTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.login(username='testuser', password='password123')

    def test_support_ticket_notifications(self):
        ticket = SupportTicket.objects.create(
            user=self.user,
            title='help',
            email='testuser@example.com',
            subject='Test Support Ticket',
            description='This is a test support ticket.'
        )
        response = self.client.post(reverse('support:send_ticket_reply', args=[ticket.ticket_id]), {
            'message': 'This is a test reply.'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SupportTicketMessage.objects.filter(ticket=ticket, message='This is a test reply.').exists())
