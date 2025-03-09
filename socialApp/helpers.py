from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Crew, CrewMember, CrewRequest
from accountManagementApp.models import UserProfile

def send_crew_request(sender, receiver_username, crew_id):
    """Send a crew invite request."""
    sender_profile = get_object_or_404(UserProfile, user=sender)
    receiver = get_object_or_404(UserProfile, user__username=receiver_username)
    crew = get_object_or_404(Crew, crewId=crew_id)

    if CrewMember.objects.filter(crew=crew, user=receiver.user).exists():
        return False, "User is already a member of the crew.", None

    crew_request, created = CrewRequest.objects.get_or_create(
        sender=sender_profile.user,
        receiver=receiver.user,
        crew=crew,
        defaults={"status": "pending"},
    )

    if not created:
        return False, "Crew request has already been sent.", None

    return True, "Crew request sent successfully.", crew_request


def leave_crew(user, crewId):
    """Leave a crew."""
    crew = get_object_or_404(Crew, crewId=crewId)
    
    crew_member = get_object_or_404(CrewMember, crew=crew, user=user)
    crew_member.delete()

    CrewRequest.objects.filter(crew=crew, receiver=user).delete()
    CrewRequest.objects.filter(crew=crew, sender=user).delete()

    if not CrewMember.objects.filter(crew=crew).exists():
        crew.delete()
        return Response({"message": f"{crew.name} crew has been deleted."}, status=200)

    return Response({"message": f"{user.username} has left the {crew.name} crew."}, status=200)


def delete_crew(user, crewId):
    """Delete a crew (Only if the user is the owner)."""
    crew = get_object_or_404(Crew, crewId=crewId)

    if crew.created_by != user:
        return Response({"error": "Only the crew owner can delete the crew."}, status=403)

    CrewRequest.objects.filter(crew=crew).delete()
    CrewMember.objects.filter(crew=crew).delete()
    crew.delete()
    
    return Response({"message": f"{crew.name} crew has been deleted."}, status=200)


def kick_member(user, crewId, member_username):
    """Kick a member from the crew."""
    crew = get_object_or_404(Crew, crewId=crewId)

    if crew.created_by != user:
        return Response({"error": "Only the crew owner can kick members."}, status=403)

    member = get_object_or_404(UserProfile, user__username=member_username)

    CrewRequest.objects.filter(crew=crew, receiver=member.user).delete()
    CrewRequest.objects.filter(crew=crew, sender=member.user).delete()
    CrewMember.objects.filter(crew=crew, user=member.user).delete()

    return Response({"message": f"{member.user.username} has been removed from {crew.name}."}, status=200)