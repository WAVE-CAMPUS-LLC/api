from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Event, HostProfile, EventPrivacy
from .serializers import EventSerializer, EventPrivacySerializer
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime
import uuid

class CreateEventAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Extract data from the request
            event_data = {
                'title': request.data.get('title'),
                'description': request.data.get('description'),
                'event_type': request.data.get('event_type'),
                'date': request.data.get('date'),
                'start_time': datetime.strptime(request.data.get('start_time'), "%H:%M").time(),  # Convert to time object
                # 'location': request.data.get('location'),
                # 'price': request.data.get('price'),
                # 'capacity': request.data.get('capacity'),
                'header_photo': request.FILES.get('header_photo'),
                'age_restriction': request.data.get('age_restriction'),
                'host': request.user,
                'status': 'incomplete',
            }

            # Create the event
            event = Event.objects.create(**event_data)

            # Serialize and return the event
            serializer = EventSerializer(event)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class SaveEventProgressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, eventId):
        """
        Save event progress (update event details).
        """
        try:
            event = get_object_or_404(Event, eventId=eventId, host=request.user)

            # Update event fields
            event.title = request.data.get("title", event.title)
            event.event_type = request.data.get("event_type", event.event_type)
            event.description = request.data.get("description", event.description)
            event.privacy = request.data.get("privacy", event.privacy)
            event.country = request.data.get("country", event.country)
            event.city = request.data.get("city", event.city)
            event.state = request.data.get("state", event.state)
            event.zip_code = request.data.get("zip_code", event.zip_code)
            # event.contact_email = request.data.get("contact_email", event.contact_email)
            # event.contact_phone = request.data.get("contact_phone", event.contact_phone)

            # Handle date and time fields
            date_str = request.data.get("date")
            if date_str:
                event.date = datetime.strptime(date_str, "%Y-%m-%d").date()

            start_time_str = request.data.get("start_time")
            if start_time_str:
                event.start_time = datetime.strptime(start_time_str, "%H:%M").time()

            end_time_str = request.data.get("end_time")
            if end_time_str:
                event.end_time = datetime.strptime(end_time_str, "%H:%M").time()

            # Save changes
            event.save()

            # Handle event privacy
            if event.privacy == "Discoverable":
                EventPrivacy.objects.create(
                    event=event,
                    display_on_explore=True,
                    require_invitation=False,
                )
            elif event.privacy == "Invite Only":
                EventPrivacy.objects.create(
                    event=event,
                    display_on_explore=False,
                    require_invitation=True,
                )

            # Serialize and return the updated event
            serializer = EventSerializer(event)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )