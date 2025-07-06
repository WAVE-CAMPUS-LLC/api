from socialGraphManagement.neo4j_client import GraphClient


def sync_membership(user_id, campus_id):
    query = """
        MERGE (u:User {id: $user})
        MERGE (c:Campus {id: $campus})
        MERGE (u)-[:MEMBER_OF]->(c)
    """
    parameters = {
        "user": str(user_id),
        "campus": str(campus_id),
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()
