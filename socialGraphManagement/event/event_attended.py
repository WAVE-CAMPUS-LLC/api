from socialGraphManagement.neo4j_client import GraphClient


def sync_event_attended(user_id: str, event_id: str, event_title: str):
    query = """
        MERGE (u:User {user_id: $user})
        MERGE (e:Event {eventId: $eventId, title: $eventTitle})
        MERGE (u)-[:ATTENDED_EVENT]->(e)
    """
    parameters = {
        "user": str(user_id),
        "eventId": str(event_id),
        "eventTitle": event_title,
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()
