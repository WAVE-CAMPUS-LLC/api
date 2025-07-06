from socialGraphManagement.neo4j_client import GraphClient


def sync_crew_membership(user_id, crew_id):
    query = """
        MERGE (u:User {id: $user})
        MERGE (c:Crew {id: $crew})
        MERGE (u)-[:MEMBER_OF]->(c)
    """
    parameters = {
        "user": str(user_id),
        "crew": str(crew_id),
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()
