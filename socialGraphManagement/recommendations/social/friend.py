from socialGraphManagement.neo4j_client import GraphClient
from openai import OpenAI
from django.conf import settings
from authenticationApp.models import CustomUser
from apiManager.utilities.notifications.send_notification import send_notification

import logging

client = OpenAI(api_key=settings.COLLEGE_OPENAI_API_KEY)


logger = logging.getLogger(__name__)


def get_friend_recommendations(user_id: str, limit: int = 5):
    query = """
        MATCH (u:User {user_id: $user_id})

        MATCH (other:User)
        WHERE other.user_id <> $user_id
        AND NOT (u)-[:FRIEND]-(other)
        AND NOT (u)-[:REQUESTED]->(other)
        AND NOT (other)-[:REQUESTED]->(u)

        OPTIONAL MATCH (u)-[:INTERESTED_IN]->(i:Interest)<-[:INTERESTED_IN]-(other)
        WITH u, other, count(i) AS shared_interests

        OPTIONAL MATCH (u)-[:ATTENDED_EVENT]->(e:Event)<-[:ATTENDED_EVENT]-(other)
        WITH u, other, shared_interests, count(e) AS shared_events

        OPTIONAL MATCH (u)-[:PREFERRED_TIME]->(t:Time)<-[:PREFERRED_TIME]-(other)
        WITH u, other, shared_interests, shared_events, count(t) AS shared_times

        OPTIONAL MATCH (u)-[:WANTS_TO_MEET]->(p:Person)<-[:WANTS_TO_MEET]-(other)
        WITH u, other, shared_interests, shared_events, shared_times, count(p) AS shared_people

        WITH u, other, shared_interests, shared_events, shared_times, shared_people,
            CASE WHEN u.vibe = other.vibe THEN 1 ELSE 0 END AS vibe_match

        OPTIONAL MATCH (u)-[:FRIEND]-(mf:User)-[:FRIEND]-(other)
        WITH other, shared_interests, shared_events, shared_times, shared_people, vibe_match,
            count(DISTINCT mf) AS mutual_friends

        WITH other.user_id AS user_id, 
            (shared_interests * 3 + 
            shared_events * 3 + 
            shared_times * 2 + 
            shared_people * 2 + 
            vibe_match * 2 + 
            mutual_friends) AS score
        ORDER BY score DESC
        LIMIT $limit
        RETURN user_id, score
        """

    parameters = {
        "user_id": str(user_id),
        "limit": limit,
    }

    graph_client = GraphClient()
    results = graph_client.run_query(query, parameters)
    graph_client.close()

    return [{"user_id": r["user_id"], "score": r["score"]} for r in results]


def get_user_by_id(user_id: str) -> str:
    return f"user_{user_id[-4:]}"


def personalize_friend_recommendations(
    user_id: str, recommendations: list[dict]
) -> str:
    names = [get_user_by_id(uid["user_id"]) for uid in recommendations]
    name_str = ", ".join(names[:3])

    prompt = f"""
        {get_user_by_id(user_id)} might get along really well with {name_str}.
        Write a short, upbeat, college-style message suggesting they check them out on the app.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You're a fun, friendly campus assistant.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content
        return (
            content if content else f"Check out your new suggested friends: {name_str}."
        )
    except Exception as e:
        logger.error("GPT personalization failed: %s", e)
        return f"Check out your new suggested friends: {name_str}."

    return prompt


def suggest_friends_for_user(user_id: str, user_name: str, limit: int = 5) -> str:
    recommendations = get_friend_recommendations(user_id, limit)
    if not recommendations:
        return (
            "We couldn't find any new friend suggestions right now. Check back later!"
        )
    return personalize_friend_recommendations(user_name, recommendations)


def get_all_users():
    """
    Get all active users from the database.
    Returns a queryset of CustomUser objects.
    """
    return CustomUser.objects.filter(is_active=True)


def send_friend_recommendation_notification(user_id: str, message: str):
    """
    Send a friend recommendation notification to a user.
    Uses the existing notification system.
    """
    try:
        # Get the user
        user = CustomUser.objects.get(user_id=user_id)

        # Send notification using the existing notification system
        send_notification(
            recipient_id=str(user.user_id),
            actor_id=None,  # No specific actor for system notifications
            notification_type="friend_connected",  # Using existing type for friend-related notifications
            content=message,
            metadata={"type": "friend_recommendation"},
        )

        logger.info("Sent friend recommendation notification to user %s", user_id)
        return True

    except CustomUser.DoesNotExist:  # type: ignore
        logger.warning(
            "User %s not found for friend recommendation notification", user_id
        )
        return False
    except Exception as e:
        logger.error(
            "Error sending friend recommendation notification to user %s: %s",
            user_id,
            e,
        )
        return False


def send_hourly_friend_recommendations():
    """
    Send friend recommendations to all active users.
    This function can be called by a scheduled task (e.g., Celery beat).
    """
    users = get_all_users()
    successful_notifications = 0
    failed_notifications = 0

    for user in users:
        try:
            # Use username or fallback to user_id if username is None
            user_name = user.username or str(user.user_id)

            # Generate personalized friend recommendation message
            message = suggest_friends_for_user(str(user.user_id), user_name)

            # Send notification
            if send_friend_recommendation_notification(str(user.user_id), message):
                successful_notifications += 1
            else:
                failed_notifications += 1

        except Exception as e:
            logger.error(
                "Error processing friend recommendation for user %s: %s",
                user.user_id,
                e,
            )
            failed_notifications += 1

    logger.info(
        "Friend recommendation batch completed. Success: %s, Failed: %s",
        successful_notifications,
        failed_notifications,
    )
    return {
        "successful_notifications": successful_notifications,
        "failed_notifications": failed_notifications,
        "total_users": users.count(),
    }
