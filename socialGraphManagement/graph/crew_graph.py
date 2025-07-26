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


def sync_crew_college_relationships(crew_id: str):
    """
    Sync crew-college relationships through crew members.
    This creates relationships between crews and colleges based on where crew members attend.
    """
    # Get all crew members with their college information
    crew_members = CrewMember.objects.filter(crew__crewId=crew_id).select_related(
        "user", "user__user_profile", "user__user_profile__college"
    )

    colleges = set()
    for member in crew_members:
        if member.user.user_profile and member.user.user_profile.college:
            colleges.add(member.user.user_profile.college)

    if not colleges:
        return

    # Create relationships between crew and colleges
    query = """
        MATCH (c:Crew {crewId: $crew_id})
        WITH c
        UNWIND $colleges as college
        MERGE (col:College {collegeId: college.collegeId, name: college.name})
        MERGE (c)-[:ASSOCIATED_WITH]->(col)
    """

    college_data = [
        {"collegeId": str(college.collegeId), "name": college.name}
        for college in colleges
    ]

    parameters = {
        "crew_id": str(crew_id),
        "colleges": college_data,
    }

    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()


def suggest_crews_for_user(user_id: str, limit: int = 10):
    """
    Suggest relevant crews for a user to join, prioritizing shared interests, college, and mutual members.
    Returns a list of crew IDs and scores.
    """
    query = """
    MATCH (u:User {user_id: $user_id})
    // Find crews the user is not a member of
    MATCH (c:Crew)
    WHERE NOT (u)-[:MEMBER_OF]->(c)
    
    // Shared interests
    OPTIONAL MATCH (u)-[:INTERESTED_IN]->(i:Interest)<-[:RELATES_TO_INTEREST]-(c)
    WITH u, c, count(i) AS shared_interests
    
    // Shared college through crew-college relationships
    OPTIONAL MATCH (u)-[:ATTENDS]->(col:College)<-[:ASSOCIATED_WITH]-(c)
    WITH u, c, shared_interests, count(DISTINCT col) AS shared_college
    
    // Mutual members
    OPTIONAL MATCH (u)-[:FRIEND]-(f:User)-[:MEMBER_OF]->(c)
    WITH c, shared_interests, shared_college, count(DISTINCT f) AS mutual_members
    
    // Score crews
    WITH c, (shared_interests * 3 + shared_college * 2 + mutual_members * 2) AS score
    ORDER BY score DESC
    RETURN c.crewId AS crew_id, c.name AS name, score
    LIMIT $limit
    """
    parameters = {"user_id": str(user_id), "limit": limit}
    graph_client = GraphClient()
    results = graph_client.run_query(query, parameters)
    graph_client.close()
    return [
        {"crew_id": record["crew_id"], "name": record["name"], "score": record["score"]}
        for record in results
    ]
