from socialGraphManagement.neo4j_client import GraphClient


def sync_event_rsvp(user_id: str, event_id: str, event_title: str = ""):
    query = """
        MERGE (u:User {user_id: $user_id})  
        MERGE (e:Event {eventId: $event_id, title: $event_title})
        MERGE (u)-[:RSVP]->(e)
    """
    parameters = {
        "user_id": str(user_id),
        "event_id": str(event_id),
        "event_title": event_title,
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()
