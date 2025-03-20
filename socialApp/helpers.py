from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Crew, CrewMember, CrewRequest
from accountManagementApp.models import UserProfile


def send_crew_request(sender, receiver_username, crew_id):
    """Send a crew invite request with optimized database queries."""
    try:
        # Get the receiver using a single efficient query with select_related
        receiver = UserProfile.objects.select_related('user').get(user__username=receiver_username)
        
        # Get the crew with select_related to avoid additional queries
        crew = Crew.objects.select_related('created_by').get(crewId=crew_id)
        
        # Check if receiver is already a member - use exists for efficiency
        if CrewMember.objects.filter(crew=crew, user=receiver.user).exists():
            return False, "User is already a member of the crew.", None

        # Use get_or_create to avoid race conditions
        crew_request, created = CrewRequest.objects.get_or_create(
            sender=sender,
            receiver=receiver.user,
            crew=crew,
            defaults={"status": "pending"},
        )

        if not created:
            return False, "Crew request has already been sent.", None

        return True, "Crew request sent successfully.", crew_request
        
    except UserProfile.DoesNotExist:
        return False, f"User {receiver_username} not found.", None
    except Crew.DoesNotExist:
        return False, "Crew not found.", None
    except Exception as e:
        return False, f"Error sending crew request: {str(e)}", None


def leave_crew(user, crewId):
    """Leave a crew with optimized database operations."""
    try:
        # Use select_related to get the crew in a single query
        crew = Crew.objects.get(crewId=crewId)
        
        # Get the crew member record
        crew_member = CrewMember.objects.get(crew=crew, user=user)
        
        # Delete in a single batch operation using filter
        CrewRequest.objects.filter(
            Q(crew=crew) & (Q(receiver=user) | Q(sender=user))
        ).delete()
        
        # Delete the membership
        crew_member.delete()
        
        # Check remaining members in a single query
        remaining_members = CrewMember.objects.filter(crew=crew).exists()
        
        # If no members left, delete the crew
        if not remaining_members:
            crew.delete()
            return Response({"message": f"You left and {crew.name} crew has been deleted as no members remain."})
            
        return Response({"message": f"You have left the {crew.name} crew."})
        
    except Crew.DoesNotExist:
        return Response({"error": "Crew not found."}, status=404)
    except CrewMember.DoesNotExist:
        return Response({"error": "You are not a member of this crew."}, status=400)
    except Exception as e:
        return Response({"error": f"Error: {str(e)}"}, status=500)


def delete_crew(user, crewId):
    """Delete a crew (only if user is the owner)."""
    try:
        # Get the crew with one query
        crew = Crew.objects.get(crewId=crewId)
        
        # Check if user is the owner
        if crew.created_by != user:
            return Response(
                {"error": "Only the crew owner can delete the crew."}, status=403
            )
            
        # Delete related objects in bulk operations
        crew_name = crew.name
        
        # Delete all requests related to this crew in one operation
        CrewRequest.objects.filter(crew=crew).delete()
        
        # Delete all memberships in one operation
        CrewMember.objects.filter(crew=crew).delete()
        
        # Finally delete the crew itself
        crew.delete()
        
        return Response({"message": f"{crew_name} crew has been deleted."})
        
    except Crew.DoesNotExist:
        return Response({"error": "Crew not found."}, status=404)
    except Exception as e:
        return Response({"error": f"Error: {str(e)}"}, status=500)


def kick_member(user, crewId, member_username):
    """Kick a member from the crew with optimized queries."""
    try:
        # Get both crew and member in efficient queries
        crew = Crew.objects.get(crewId=crewId)
        member_user = get_object_or_404(UserProfile, user__username=member_username).user
        
        # Verify user is admin/owner
        if crew.created_by != user:
            crew_member = CrewMember.objects.filter(crew=crew, user=user, is_admin=True).first()
            if not crew_member:
                return Response(
                    {"error": "Only crew admins can kick members."}, status=403
                )
        
        # Check if target user is in crew
        if not CrewMember.objects.filter(crew=crew, user=member_user).exists():
            return Response({"error": f"{member_username} is not in this crew."}, status=400)
            
        # Cannot kick the owner
        if crew.created_by == member_user:
            return Response({"error": "You cannot kick the crew owner."}, status=400)
        
        # Delete all related requests in bulk
        CrewRequest.objects.filter(
            Q(crew=crew) & (Q(receiver=member_user) | Q(sender=member_user))
        ).delete()
        
        # Delete membership
        CrewMember.objects.filter(crew=crew, user=member_user).delete()
        
        return Response(
            {"message": f"{member_username} has been removed from the crew."}
        )
        
    except Crew.DoesNotExist:
        return Response({"error": "Crew not found."}, status=404)
    except Exception as e:
        return Response({"error": f"Error: {str(e)}"}, status=500)