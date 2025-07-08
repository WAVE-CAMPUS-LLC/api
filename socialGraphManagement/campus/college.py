from socialGraphManagement.neo4j_client import GraphClient


def sync_user_college(user_id: str, collegeId: str, collegeName: str):
    query = """
        MERGE (u:User {user_id: $user_id})
        MERGE (c:College {collegeId: $collegeId, name: $collegeName})
        MERGE (u)-[:ATTENDS]->(c)
    """
    parameters = {
        "user_id": str(user_id),
        "collegeId": str(collegeId),
        "collegeName": collegeName,
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()


def remove_user_from_college(user_id: str, collegeId: str):
    query = """
        MATCH (u:User {user_id: $user_id})-[r:ATTENDS]->(c:College {collegeId: $collegeId})
        DELETE r
    """
    parameters = {
        "user_id": str(user_id),
        "collegeId": str(collegeId),
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()
