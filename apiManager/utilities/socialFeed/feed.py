from socialGraphManagement.neo4j_client import GraphClient


def get_friendship_feed_from_graph(user_id):
    query = """
        MATCH (me:User {id: $user_id})-[:FRIEND]->(f:User)-[:FRIEND]->(fof:User)
        WHERE NOT (me)-[:FRIEND]->(fof) AND me <> fof
        RETURN f.id AS friend_id, fof.id AS new_friend_id
        LIMIT 20
    """
    graph_client = GraphClient()
    results = graph_client.run_query(query, {"user_id": str(user_id)})

    # Format results
    return [
        {
            "type": "graph_friendship",
            "friend_id": record["friend_id"],
            "new_friend_id": record["new_friend_id"],
        }
        for record in results
    ]
