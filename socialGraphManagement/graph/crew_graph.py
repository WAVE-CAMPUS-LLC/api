from socialGraphManagement.neo4j_client import GraphClient
from socialApp.models import Crew, CrewMember
from authenticationApp.models import CustomUser
from accountManagementApp.models import UserPreferences
from socialGraphManagement.event.event_based_preferences import get_user_preferences


def sync_crew_node(crew_id: str, name: str, bio: str = "", crew_image_url: str = None):
    query = """
        MERGE (c:Crew {crewId: $crew_id})
        SET c.name = $name, c.bio = $bio, c.crew_image = $crew_image
    """
    parameters = {
        "crew_id": str(crew_id),
        "name": name,
        "bio": bio or "",
        "crew_image": crew_image_url or "",
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()


def sync_crew_membership(user_id: str, crew_id: str):
    query = """
        MERGE (u:User {user_id: $user_id})
        MERGE (c:Crew {crewId: $crew_id})
        MERGE (u)-[:MEMBER_OF]->(c)
    """
    parameters = {
        "user_id": str(user_id),
        "crew_id": str(crew_id),
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()


def aggregate_crew_interests(crew_id: str):
    # Get all members of the crew
    member_ids = CrewMember.objects.filter(crew__crewId=crew_id).values_list(
        "user__user_id", flat=True
    )
    all_interests = set()
    for user_id in member_ids:
        prefs = get_user_preferences(str(user_id))
        for interest in prefs.get("interests", []):
            if interest:
                all_interests.add(interest)
    # Update the Crew node with the aggregated interests
    query = """
        MATCH (c:Crew {crewId: $crew_id})
        SET c.interests = $interests
    """
    parameters = {
        "crew_id": str(crew_id),
        "interests": list(all_interests),
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()
