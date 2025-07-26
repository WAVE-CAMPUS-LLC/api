from socialGraphManagement.neo4j_client import GraphClient


def sync_event_host(event_id: str, event_title: str, host_id: str):
    """
    Sync event-host relationship to the graph database.
    """
    query = """
        MERGE (e:Event {eventId: $event_id, title: $event_title})
        MERGE (h:User {user_id: $host_id})
        MERGE (h)-[:HOSTED]->(e)
    """
    parameters = {
        "event_id": str(event_id),
        "event_title": event_title,
        "host_id": str(host_id),
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()


def remove_event_host(event_id: str, host_id: str):
    """
    Remove event-host relationship from the graph database.
    """
    query = """
        MATCH (h:User {user_id: $host_id})-[r:HOSTED]->(e:Event {eventId: $event_id})
        DELETE r
    """
    parameters = {
        "event_id": str(event_id),
        "host_id": str(host_id),
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()
