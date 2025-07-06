from socialGraphManagement.neo4j_client import GraphClient


def sync_friendship(user_one_id, user_two_id):
    query = """
        MERGE (u1:User {id: $user1})
        MERGE (u2:User {id: $user2})
        MERGE (u1)-[:FRIEND]->(u2)
        MERGE (u2)-[:FRIEND]->(u1)
    """
    parameters = {
        "user1": str(user_one_id),
        "user2": str(user_two_id),
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()


def remove_friendship(user_one_id, user_two_id):
    query = """
        MATCH (u1:User {id: $user1})-[r1:FRIEND]-(u2:User {id: $user2})
        DELETE r1
    """
    parameters = {
        "user1": str(user_one_id),
        "user2": str(user_two_id),
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()
