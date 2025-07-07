from socialGraphManagement.neo4j_client import GraphClient
import logging

logger = logging.getLogger(__name__)


def create_friend_request(sender_id: str, receiver_id: str):
    if str(sender_id) == str(receiver_id):
        logger.warning(
            "Skipping self-request: %s tried to add themselves as a friend", sender_id
        )
        return
    query = """
    MERGE (sender: User {user_id: $sender_id})
    MERGE (receiver: User {user_id: $receiver_id})
    MERGE (sender)-[:REQUESTED]->(receiver)
    """
    parameters = {
        "sender_id": str(sender_id),
        "receiver_id": str(receiver_id),
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()


def sync_friendship(user_one_id: str, user_two_id: str):
    if str(user_one_id) == str(user_two_id):
        logger.warning(
            "Skipping sync_friendship: user %s tried to friend themselves", user_one_id
        )
        return
    query = """
    MATCH (u1:User {user_id: $user1}), (u2:User {user_id: $user2})
    MERGE (u1)-[:FRIEND]->(u2)
    MERGE (u2)-[:FRIEND]->(u1)
    WITH u1, u2
    OPTIONAL MATCH (u1)-[r1:REQUESTED]->(u2)
    DELETE r1
    WITH u1, u2
    OPTIONAL MATCH (u2)-[r2:REQUESTED]->(u1)
    DELETE r2
    """
    parameters = {
        "user1": str(user_one_id),
        "user2": str(user_two_id),
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()


def remove_friendship(user_one_id: str, user_two_id: str):
    if str(user_one_id) == str(user_two_id):
        logger.warning(
            "Skipping remove_friendship: user %s tried to remove themselves as a friend",
            user_one_id,
        )
        return
    query = """
        MATCH (u1:User {user_id: $user1})-[r1:FRIEND]->(u2:User {user_id: $user2})
        DELETE r1
        WITH u1, u2
        MATCH (u2:User {user_id: $user2})-[r2:FRIEND]->(u1:User {user_id: $user1})
        DELETE r2
    """
    parameters = {
        "user1": str(user_one_id),
        "user2": str(user_two_id),
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()


def remove_friend_request(sender_id: str, receiver_id: str):
    if str(sender_id) == str(receiver_id):
        logger.warning(
            "Skipping remove_friend_request: user %s tried to remove themselves as a friend",
            sender_id,
        )
        return
    query = """
    MATCH (sender:User {user_id: $sender_id})-[r:REQUESTED]->(receiver:User {user_id: $receiver_id})
    DELETE r
    """
    parameters = {
        "sender_id": str(sender_id),
        "receiver_id": str(receiver_id),
    }
    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()
