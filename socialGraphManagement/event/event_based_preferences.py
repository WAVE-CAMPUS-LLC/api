from socialGraphManagement.neo4j_client import GraphClient
import logging

logger = logging.getLogger(__name__)


def sync_event_preferences(
    event_id: str,
    event_title: str,
    event_type: str,
    event_description: str = "",
    custom_interests: list | None = None,
):
    """
    Sync event preferences to the graph based on event characteristics.
    This creates relationships between events and preference categories.
    Supports both automatic keyword extraction and custom interests.
    """
    # Combine automatic and custom interests
    auto_interests = []
    if event_description:
        desc_lower = event_description.lower()
        if any(word in desc_lower for word in ["music", "concert", "band", "dj"]):
            auto_interests.append("Music")
        if any(
            word in desc_lower
            for word in ["sport", "fitness", "workout", "gym", "running"]
        ):
            auto_interests.append("Sports")
        if any(
            word in desc_lower
            for word in ["art", "gallery", "exhibition", "painting", "sculpture"]
        ):
            auto_interests.append("Art")
        if any(
            word in desc_lower
            for word in ["tech", "coding", "programming", "software", "app"]
        ):
            auto_interests.append("Technology")
        if any(
            word in desc_lower
            for word in ["food", "cooking", "restaurant", "cuisine", "chef"]
        ):
            auto_interests.append("Food")
        if any(word in desc_lower for word in ["dance", "party", "club", "nightlife"]):
            auto_interests.append("Dance")
        if any(
            word in desc_lower
            for word in ["business", "networking", "career", "professional"]
        ):
            auto_interests.append("Business")
        if any(
            word in desc_lower for word in ["game", "gaming", "esports", "video game"]
        ):
            auto_interests.append("Gaming")
        if any(
            word in desc_lower for word in ["book", "reading", "literature", "author"]
        ):
            auto_interests.append("Reading")
        if any(
            word in desc_lower
            for word in ["travel", "adventure", "exploration", "trip"]
        ):
            auto_interests.append("Travel")

    # Add custom interests
    all_interests = list(set(auto_interests + (custom_interests or [])))

    # Determine time preference based on event type
    time_mapping = {
        "Party": "Night",
        "Nightlife": "Night",
        "Concert": "Night",
        "Workshop": "Day",
        "Seminar": "Day",
        "Conference": "Day",
        "Sports": "Morning",
        "Fitness": "Morning",
        "Outdoor": "Morning",
        "Dinner": "Evening",
        "Social": "Evening",
        "Networking": "Evening",
    }
    time_pref = time_mapping.get(event_type, "Day")

    # Determine people preference based on event type
    people_mapping = {
        "Networking": "Professionals",
        "Business": "Professionals",
        "Conference": "Professionals",
        "Party": "Social People",
        "Social": "Social People",
        "Dance": "Social People",
        "Workshop": "Learners",
        "Learning": "Learners",
        "Seminar": "Learners",
        "Sports": "Active People",
        "Fitness": "Active People",
        "Outdoor": "Active People",
        "Art": "Creative People",
        "Gallery": "Creative People",
        "Exhibition": "Creative People",
    }
    people_pref = people_mapping.get(event_type, "General")

    query = """
    MERGE (e:Event {eventId: $event_id, title: $event_title})
    SET e.event_type = $event_type, e.description = $event_description
    
    // Connect event to its type category
    MERGE (et:EventType {name: $event_type})
    MERGE (e)-[:IS_TYPE]->(et)
    
    // Connect all interests (both automatic and custom)
    WITH e
    UNWIND $interests as interest
    MERGE (i:Interest {name: interest})
    MERGE (e)-[:RELATES_TO_INTEREST]->(i)
    
    // Connect event to time preference
    WITH e
    MERGE (t:Time {name: $time_pref})
    MERGE (e)-[:BEST_TIME]->(t)
    
    // Connect event to people preference
    WITH e
    MERGE (p:Person {name: $people_pref})
    MERGE (e)-[:ATTRACTS_PEOPLE]->(p)
    """

    parameters = {
        "event_id": str(event_id),
        "event_title": event_title,
        "event_type": event_type,
        "event_description": event_description or "",
        "interests": all_interests,
        "time_pref": time_pref,
        "people_pref": people_pref,
    }

    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()


def get_event_recommendations_for_user(user_id: str, limit: int = 10):
    """
    Get event recommendations for a user based on their preferences.
    """
    query = """
    MATCH (u:User {user_id: $user_id})
    
    // Get user's interests
    OPTIONAL MATCH (u)-[:INTERESTED_IN]->(user_interests:Interest)
    
    // Get user's preferred times
    OPTIONAL MATCH (u)-[:PREFERRED_TIME]->(user_times:Time)
    
    // Get user's preferred people types
    OPTIONAL MATCH (u)-[:WANTS_TO_MEET]->(user_people:Person)
    
    // Find events that match user preferences
    WITH u, collect(user_interests) as user_interests, collect(user_times) as user_times, collect(user_people) as user_people
    
    MATCH (e:Event)
    WHERE e.eventId IS NOT NULL
    
    // Calculate match score based on preferences
    WITH e, u, user_interests, user_times, user_people,
         size([i IN user_interests WHERE (e)-[:RELATES_TO_INTEREST]->(i)]) as interest_matches,
         size([t IN user_times WHERE (e)-[:BEST_TIME]->(t)]) as time_matches,
         size([p IN user_people WHERE (e)-[:ATTRACTS_PEOPLE]->(p)]) as people_matches
    
    // Calculate total score (weighted)
    WITH e, u, interest_matches, time_matches, people_matches,
         (interest_matches * 3 + time_matches * 2 + people_matches * 1) as total_score
    
    // Filter out events user has already interacted with
    WHERE NOT (u)-[:ATTENDED_EVENT]->(e)
    AND NOT (u)-[:GOING_TO]->(e)
    AND NOT (u)-[:RSVP]->(e)
    AND NOT (u)-[:FAVORITED_EVENT]->(e)
    
    RETURN e.eventId as event_id, e.title as title, e.event_type as event_type, total_score
    ORDER BY total_score DESC
    LIMIT $limit
    """

    parameters = {
        "user_id": str(user_id),
        "limit": limit,
    }

    graph_client = GraphClient()
    results = graph_client.run_query(query, parameters)
    graph_client.close()

    return [
        {
            "event_id": record["event_id"],
            "title": record["title"],
            "event_type": record["event_type"],
            "match_score": record["total_score"],
        }
        for record in results
    ]


def get_users_for_event_recommendation(event_id: str, limit: int = 20):
    """
    Get users who would be most interested in a specific event.
    """
    query = """
    MATCH (e:Event {eventId: $event_id})
    
    // Get event's interests
    OPTIONAL MATCH (e)-[:RELATES_TO_INTEREST]->(event_interests:Interest)
    
    // Get event's best time
    OPTIONAL MATCH (e)-[:BEST_TIME]->(event_time:Time)
    
    // Get event's target people
    OPTIONAL MATCH (e)-[:ATTRACTS_PEOPLE]->(event_people:Person)
    
    // Find users who match event preferences
    WITH e, collect(event_interests) as event_interests, collect(event_time) as event_time, collect(event_people) as event_people
    
    MATCH (u:User)
    WHERE u.user_id IS NOT NULL
    
    // Calculate match score
    WITH e, u, event_interests, event_time, event_people,
         size([i IN event_interests WHERE (u)-[:INTERESTED_IN]->(i)]) as interest_matches,
         size([t IN event_time WHERE (u)-[:PREFERRED_TIME]->(t)]) as time_matches,
         size([p IN event_people WHERE (u)-[:WANTS_TO_MEET]->(p)]) as people_matches
    
    // Calculate total score
    WITH e, u, interest_matches, time_matches, people_matches,
         (interest_matches * 3 + time_matches * 2 + people_matches * 1) as total_score
    
    // Filter out users who have already interacted with this event
    WHERE NOT (u)-[:ATTENDED_EVENT]->(e)
    AND NOT (u)-[:GOING_TO]->(e)
    AND NOT (u)-[:RSVP]->(e)
    AND NOT (u)-[:FAVORITED_EVENT]->(e)
    
    RETURN u.user_id as user_id, total_score
    ORDER BY total_score DESC
    LIMIT $limit
    """

    parameters = {
        "event_id": str(event_id),
        "limit": limit,
    }

    graph_client = GraphClient()
    results = graph_client.run_query(query, parameters)
    graph_client.close()

    return [
        {
            "user_id": record["user_id"],
            "match_score": record["total_score"],
        }
        for record in results
    ]


def get_similar_events(event_id: str, limit: int = 5):
    """
    Find events similar to a given event based on shared characteristics.
    """
    query = """
    MATCH (target:Event {eventId: $event_id})
    
    // Get target event's characteristics
    OPTIONAL MATCH (target)-[:RELATES_TO_INTEREST]->(target_interests:Interest)
    OPTIONAL MATCH (target)-[:BEST_TIME]->(target_time:Time)
    OPTIONAL MATCH (target)-[:ATTRACTS_PEOPLE]->(target_people:Person)
    OPTIONAL MATCH (target)-[:IS_TYPE]->(target_type:EventType)
    
    // Find other events with similar characteristics
    WITH target, collect(target_interests) as target_interests, collect(target_time) as target_time, 
         collect(target_people) as target_people, collect(target_type) as target_type
    
    MATCH (similar:Event)
    WHERE similar.eventId <> $event_id
    
    // Calculate similarity score
    WITH target, similar, target_interests, target_time, target_people, target_type,
         size([i IN target_interests WHERE (similar)-[:RELATES_TO_INTEREST]->(i)]) as interest_similarity,
         size([t IN target_time WHERE (similar)-[:BEST_TIME]->(t)]) as time_similarity,
         size([p IN target_people WHERE (similar)-[:ATTRACTS_PEOPLE]->(p)]) as people_similarity,
         size([et IN target_type WHERE (similar)-[:IS_TYPE]->(et)]) as type_similarity
    
    // Calculate total similarity score
    WITH similar, interest_similarity, time_similarity, people_similarity, type_similarity,
         (interest_similarity * 3 + time_similarity * 2 + people_similarity * 2 + type_similarity * 4) as similarity_score
    
    RETURN similar.eventId as event_id, similar.title as title, similar.event_type as event_type, similarity_score
    ORDER BY similarity_score DESC
    LIMIT $limit
    """

    parameters = {
        "event_id": str(event_id),
        "limit": limit,
    }

    graph_client = GraphClient()
    results = graph_client.run_query(query, parameters)
    graph_client.close()

    return [
        {
            "event_id": record["event_id"],
            "title": record["title"],
            "event_type": record["event_type"],
            "similarity_score": record["similarity_score"],
        }
        for record in results
    ]


def add_custom_user_interest(user_id: str, interest_name: str):
    """
    Add a custom interest for a user.
    """
    query = """
    MERGE (u:User {user_id: $user_id})
    MERGE (i:Interest {name: $interest_name})
    MERGE (u)-[:INTERESTED_IN]->(i)
    """

    parameters = {
        "user_id": str(user_id),
        "interest_name": interest_name,
    }

    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()


def remove_custom_user_interest(user_id: str, interest_name: str):
    """
    Remove a custom interest for a user.
    """
    query = """
    MATCH (u:User {user_id: $user_id})-[r:INTERESTED_IN]->(i:Interest {name: $interest_name})
    DELETE r
    """

    parameters = {
        "user_id": str(user_id),
        "interest_name": interest_name,
    }

    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()


def add_custom_user_time_preference(user_id: str, time_name: str):
    """
    Add a custom time preference for a user.
    """
    query = """
    MERGE (u:User {user_id: $user_id})
    MERGE (t:Time {name: $time_name})
    MERGE (u)-[:PREFERRED_TIME]->(t)
    """

    parameters = {
        "user_id": str(user_id),
        "time_name": time_name,
    }

    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()


def add_custom_user_people_preference(user_id: str, people_name: str):
    """
    Add a custom people preference for a user.
    """
    query = """
    MERGE (u:User {user_id: $user_id})
    MERGE (p:Person {name: $people_name})
    MERGE (u)-[:WANTS_TO_MEET]->(p)
    """

    parameters = {
        "user_id": str(user_id),
        "people_name": people_name,
    }

    graph_client = GraphClient()
    graph_client.run_query(query, parameters)
    graph_client.close()


def get_user_preferences(user_id: str):
    """
    Get all preferences for a user.
    """
    query = """
    MATCH (u:User {user_id: $user_id})
    
    // Get user's interests
    OPTIONAL MATCH (u)-[:INTERESTED_IN]->(interests:Interest)
    
    // Get user's preferred times
    OPTIONAL MATCH (u)-[:PREFERRED_TIME]->(times:Time)
    
    // Get user's preferred people types
    OPTIONAL MATCH (u)-[:WANTS_TO_MEET]->(people:Person)
    
    RETURN collect(DISTINCT interests.name) as interests,
           collect(DISTINCT times.name) as times,
           collect(DISTINCT people.name) as people
    """

    parameters = {
        "user_id": str(user_id),
    }

    graph_client = GraphClient()
    results = graph_client.run_query(query, parameters)
    graph_client.close()

    if results:
        record = results[0]
        return {
            "interests": record["interests"] or [],
            "times": record["times"] or [],
            "people": record["people"] or [],
        }
    return {"interests": [], "times": [], "people": []}


def get_all_available_preferences():
    """
    Get all available preference categories from the graph.
    """
    query = """
    // Get all interests
    MATCH (i:Interest)
    WITH collect(DISTINCT i.name) as interests
    
    // Get all times
    MATCH (t:Time)
    WITH interests, collect(DISTINCT t.name) as times
    
    // Get all people types
    MATCH (p:Person)
    WITH interests, times, collect(DISTINCT p.name) as people
    
    // Get all event types
    MATCH (et:EventType)
    WITH interests, times, people, collect(DISTINCT et.name) as event_types
    
    RETURN interests, times, people, event_types
    """

    graph_client = GraphClient()
    results = graph_client.run_query(query, parameters={})
    graph_client.close()

    if results:
        record = results[0]
        return {
            "interests": record["interests"] or [],
            "times": record["times"] or [],
            "people": record["people"] or [],
            "event_types": record["event_types"] or [],
        }
    return {"interests": [], "times": [], "people": [], "event_types": []}
