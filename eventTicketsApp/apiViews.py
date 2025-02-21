from datetime import datetime
import time
import json
import stripe
from django import forms
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from eventManagementApp.models import Event, HostProfile
from .serializers import EventSerializer
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime

from wave_v1.decorators import host, check_suspension
from accountManagementApp.models import UserProfile
from collegeManagementApp.models import Organization, OrganizationMembership
from .models import Ticket, RSVPTicket
from .serializers import TicketSerializer, RSVPTicketSerializer
from authenticationApp.models import CustomUser


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_event_tickets(request, event_id):
    event = get_object_or_404(Event, eventId=event_id)
    tickets = Ticket.objects.filter(event=event)
    rsvp_tickets = RSVPTicket.objects.filter(event=event)
    return Response(
        {
            "tickets": TicketSerializer(tickets, many=True).data,
            "rsvpTickets": RSVPTicketSerializer(rsvp_tickets, many=True).data,},
        status=status.HTTP_200_OK,
    )
    
    
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_ticket_details(request, ticketId):
    ticket = get_object_or_404(Ticket, ticketId=ticketId)
    return Response(TicketSerializer(ticket).data, status=status.HTTP_200_OK)