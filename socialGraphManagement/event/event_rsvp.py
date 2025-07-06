from socialGraphManagement.neo4j_client import GraphClient


def sync_event_rsvp(user_id, event_id):
    query = """
        MERGE (u:User {id: $user})  
        MERGE (e:Event {id: $event})
        MERGE (u)-[:RSVP]->(e)
    """
    parameters = {
        "user": str(user_id),
        "event": str(event_id),
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()
