from socialGraphManagement.neo4j_client import GraphClient


def sync_event_favorited(user_id: str, event_id: str, event_title: str):
    query = """
        MERGE (u:User {user_id: $user_id})
        MERGE (e:Event {eventId: $eventId, title: $eventTitle})
        MERGE (u)-[:FAVORITED_EVENT]->(e)
    """
    parameters = {
        "user_id": str(user_id),
        "eventId": str(event_id),
        "eventTitle": event_title,
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()


def remove_event_favorited(user_id: str, event_id: str):
    query = """
        MATCH (u:User {user_id: $user_id})-[r:FAVORITED_EVENT]->(e:Event {eventId: $eventId})
        DELETE r
    """
    parameters = {
        "user_id": str(user_id),
        "eventId": str(event_id),
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()
