from socialGraphManagement.neo4j_client import GraphClient
import logging

logger = logging.getLogger(__name__)


def sync_user_preferences(
    user_id: str, vibe: str, interests: list, times: list, people_to_meet: list
):
    query = """
    MERGE (u:User {user_id: $user_id})
    SET u.vibe = $vibe
    
    FOREACH (interest IN $interests |
        MERGE (i:Interest {name: interest})
        MERGE (u)-[:INTERESTED_IN]->(i)
    )
    
    FOREACH (time IN $times |
        MERGE (t:Time {name: time})
        MERGE (u)-[:PREFERRED_TIME]->(t)
    )
    
    FOREACH (person IN $people_to_meet |
        MERGE (p:Person {name: person})
        MERGE (u)-[:WANTS_TO_MEET]->(p)
    )
    """

    parameters = {
        "user_id": str(user_id),
        "vibe": vibe,
        "interests": interests,
        "times": times,
        "people_to_meet": people_to_meet,
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()
