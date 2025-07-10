from typing import Optional, List, Dict, Any
from socialGraphManagement.neo4j_client import GraphClient
from eventManagementApp.models import Event


def get_event_recommendations_for_user(
    user_id: str, college_name: Optional[str] = None, limit: int = 10
):
    query = """
    MATCH (u:User {user_id: $user_id})
    
    // Get user's preferences from UserPreferences model
    OPTIONAL MATCH (u)-[:HAS_PREFERENCES]->(prefs:UserPreferences)
    
    // 1. Friends who have attended similar events (weight: 4)
    OPTIONAL MATCH (u)-[:FRIEND]->(f:User)-[:ATTENDED_EVENT]->(e1:Event)
    WITH u, prefs, collect(DISTINCT e1) as friend_attended_events
    
    // 2. Friends who are going to current events (weight: 5)
    OPTIONAL MATCH (u)-[:FRIEND]->(f2:User)-[:RSVP]->(e2:Event)
    WHERE e2.eventDate >= datetime()
    WITH u, prefs, friend_attended_events, collect(DISTINCT e2) as friend_rsvp_events
    
    // 3. Mutual friends who are going to events (weight: 3)
    OPTIONAL MATCH (u)-[:FRIEND]->(mf:User)-[:FRIEND]->(other:User)-[:RSVP]->(e3:Event)
    WHERE e3.eventDate >= datetime()
    WITH u, prefs, friend_attended_events, friend_rsvp_events, collect(DISTINCT e3) as mutual_events
    
    // 4. Events hosted by users from same college (weight: 3) - only if college is specified
    OPTIONAL MATCH (e4:Event)<-[:HOSTED]-(host:User)
    WHERE $college_name IS NOT NULL AND host.college = $college_name
    WITH u, prefs, friend_attended_events, friend_rsvp_events, mutual_events, collect(DISTINCT e4) as college_host_events
    
    // 5. Events where other college members are going (weight: 2) - only if college is specified
    OPTIONAL MATCH (e5:Event)<-[:RSVP]-(college_user:User)
    WHERE $college_name IS NOT NULL AND college_user.college = $college_name AND college_user.user_id <> $user_id
    WITH u, prefs, friend_attended_events, friend_rsvp_events, mutual_events, college_host_events, collect(DISTINCT e5) as college_rsvp_events
    
    // 6. Events matching user preferences (weight: 4)
    OPTIONAL MATCH (e6:Event)
    WHERE (prefs.preferred_times IS NOT NULL AND e6.best_time IN prefs.preferred_times)
       OR (prefs.people_to_meet IS NOT NULL AND ANY(person IN e6.attracts_people WHERE person IN prefs.people_to_meet))
       OR (prefs.interests IS NOT NULL AND ANY(interest IN e6.interests WHERE interest IN prefs.interests))
    WITH u, prefs, friend_attended_events, friend_rsvp_events, mutual_events, college_host_events, college_rsvp_events, collect(DISTINCT e6) as preference_events
    
    // 7. Events related to user's interests (weight: 3)
    OPTIONAL MATCH (u)-[:INTERESTED_IN]->(i:Interest)<-[:RELATES_TO_INTEREST]-(e7:Event)
    WITH u, prefs, friend_attended_events, friend_rsvp_events, mutual_events, college_host_events, college_rsvp_events, preference_events, collect(DISTINCT e7) as interest_events
    
    // 8. Events at preferred times (weight: 2)
    OPTIONAL MATCH (u)-[:PREFERRED_TIME]->(t:Time)<-[:BEST_TIME]-(e8:Event)
    WITH u, prefs, friend_attended_events, friend_rsvp_events, mutual_events, college_host_events, college_rsvp_events, preference_events, interest_events, collect(DISTINCT e8) as time_events
    
    // 9. Events that attract people user wants to meet (weight: 3)
    OPTIONAL MATCH (u)-[:WANTS_TO_MEET]->(p:Person)<-[:ATTRACTS_PEOPLE]-(e9:Event)
    WITH u, prefs, friend_attended_events, friend_rsvp_events, mutual_events, college_host_events, college_rsvp_events, preference_events, interest_events, time_events, collect(DISTINCT e9) as people_events
    
    // Combine all events and calculate weighted scores
    WITH u, friend_attended_events, friend_rsvp_events, mutual_events, college_host_events, 
         college_rsvp_events, preference_events, interest_events, time_events, people_events,
         friend_attended_events + friend_rsvp_events + mutual_events + college_host_events + 
         college_rsvp_events + preference_events + interest_events + time_events + people_events as all_events
    
    UNWIND all_events as event
    WITH event, friend_attended_events, friend_rsvp_events, mutual_events, college_host_events,
         college_rsvp_events, preference_events, interest_events, people_events, time_events,
         // Calculate weighted score based on which list the event appears in
         CASE 
             WHEN event IN friend_rsvp_events THEN 5
             WHEN event IN friend_attended_events THEN 4
             WHEN event IN preference_events THEN 4
             WHEN event IN mutual_events THEN 3
             WHEN event IN college_host_events THEN 3
             WHEN event IN interest_events THEN 3
             WHEN event IN people_events THEN 3
             WHEN event IN college_rsvp_events THEN 2
             WHEN event IN time_events THEN 2
             ELSE 1
         END as base_score
    
    // Add bonus for events happening soon
    WITH event, base_score,
         CASE 
             WHEN event.eventDate <= datetime() + duration('P7D') THEN 2  // Next 7 days
             WHEN event.eventDate <= datetime() + duration('P14D') THEN 1  // Next 14 days
             ELSE 0
         END as time_bonus
    
    WITH event, base_score + time_bonus as final_score
    
    RETURN event.eventId as event_id,
           final_score as score
    ORDER BY final_score DESC
    LIMIT $limit
    """

    parameters = {
        "user_id": user_id,
        "college_name": college_name,
        "limit": limit,
    }

    graph_client = GraphClient()
    results = graph_client.run_query(query, parameters)
    graph_client.close()

    return [
        {
            "event_id": record["event_id"],
            "match_score": record["score"],
        }
        for record in results
    ]


def get_event_details_from_ids(
    event_recommendations: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Fetch event details from database using event IDs from Neo4j recommendations.
    Returns events with title, header_photo, and event_id.
    """
    if not event_recommendations:
        return []

    # Extract event IDs from recommendations
    event_ids = []
    for rec in event_recommendations:
        try:
            # Validate UUID format
            import uuid

            uuid.UUID(rec["event_id"])
            event_ids.append(rec["event_id"])
        except (ValueError, TypeError):
            # Skip invalid UUIDs
            continue

    if not event_ids:
        return []

    # Fetch events from database
    events = Event.objects.filter(eventId__in=event_ids)

    # Create a mapping of event_id to event object for efficient lookup
    event_map = {str(event.eventId): event for event in events}

    # Build response maintaining the original order and scores
    detailed_recommendations = []
    for rec in event_recommendations:
        event_id = rec["event_id"]
        if event_id in event_map:
            event = event_map[event_id]
            detailed_recommendations.append(
                {
                    "event_id": str(event.eventId),
                    "title": event.title,
                    "header_photo": (
                        event.header_photo.url if event.header_photo else None
                    ),
                    "match_score": rec["match_score"],
                }
            )

    return detailed_recommendations


def get_users_for_event_recommendation(event_id: str, limit: int = 20):
    query = """
    MATCH (e:Event {eventId: $event_id})
    
    // 1. Friends of the host (weight: 5)
    OPTIONAL MATCH (e)-[:HOSTED]->(host:User)-[:FRIEND]->(f1:User)
    WHERE f1.user_id <> host.user_id
    WITH e, collect(DISTINCT f1) as host_friends
    
    // 2. Friends who have attended similar events (weight: 4)
    OPTIONAL MATCH (e)-[:HOSTED]->(host:User)-[:FRIEND]->(f2:User)-[:ATTENDED_EVENT]->(similar:Event)
    WHERE similar.eventId <> e.eventId AND similar.category = e.category
    WITH e, host_friends, collect(DISTINCT f2) as similar_event_friends
    
    // 3. Users from same college as host (weight: 3)
    OPTIONAL MATCH (e)-[:HOSTED]->(host:User)
    OPTIONAL MATCH (college_user:User)
    WHERE college_user.college = host.college AND college_user.user_id <> host.user_id
    WITH e, host_friends, similar_event_friends, collect(DISTINCT college_user) as college_users
    
    // 4. Users with similar interests as the event (weight: 3)
    OPTIONAL MATCH (e)-[:RELATES_TO_INTEREST]->(i:Interest)<-[:INTERESTED_IN]-(interest_user:User)
    WITH e, host_friends, similar_event_friends, college_users, collect(DISTINCT interest_user) as interest_users
    
    // 5. Users who want to meet people the event attracts (weight: 3)
    OPTIONAL MATCH (e)-[:ATTRACTS_PEOPLE]->(p:Person)<-[:WANTS_TO_MEET]-(meet_user:User)
    WITH e, host_friends, similar_event_friends, college_users, interest_users, collect(DISTINCT meet_user) as meet_users
    
    // 6. Users who prefer the event's time (weight: 2)
    OPTIONAL MATCH (e)-[:BEST_TIME]->(t:Time)<-[:PREFERRED_TIME]-(time_user:User)
    WITH e, host_friends, similar_event_friends, college_users, interest_users, meet_users, collect(DISTINCT time_user) as time_users
    
    // 7. Mutual friends of people already RSVP'd (weight: 2)
    OPTIONAL MATCH (e)-[:RSVP]-(rsvp_user:User)-[:FRIEND]->(mutual:User)
    WHERE mutual.user_id <> rsvp_user.user_id
    WITH e, host_friends, similar_event_friends, college_users, interest_users, meet_users, time_users, collect(DISTINCT mutual) as mutual_users
    
    // Combine all users and calculate scores
    WITH e, 
         host_friends + similar_event_friends + college_users + interest_users + 
         meet_users + time_users + mutual_users as all_users
    
    UNWIND all_users as user
    WITH user, e,
         // Calculate weighted score based on which list the user appears in
         CASE 
             WHEN user IN host_friends THEN 5
             WHEN user IN similar_event_friends THEN 4
             WHEN user IN interest_users THEN 3
             WHEN user IN meet_users THEN 3
             WHEN user IN college_users THEN 3
             WHEN user IN time_users THEN 2
             WHEN user IN mutual_users THEN 2
             ELSE 1
         END as base_score
    
    // Add bonus for users who are active recently
    WITH user, e, base_score,
         CASE 
             WHEN user.last_active >= datetime() - duration('P7D') THEN 1
             ELSE 0
         END as activity_bonus
    
    WITH user, e, base_score + activity_bonus as final_score
    
    RETURN user.user_id as user_id,
           user.username as username,
           user.first_name as first_name,
           user.last_name as last_name,
           final_score as score
    ORDER BY final_score DESC
    LIMIT $limit
    """

    parameters = {"event_id": event_id, "limit": limit}

    graph_client = GraphClient()
    results = graph_client.run_query(query, parameters)
    graph_client.close()

    return [
        {
            "user_id": record["user_id"],
            "username": record["username"],
            "first_name": record["first_name"],
            "last_name": record["last_name"],
            "match_score": record["score"],
        }
        for record in results
    ]


def get_similar_events(event_id: str, limit: int = 5):
    query = """
    MATCH (e:Event {eventId: $event_id})
    
    // 1. Events with same category (weight: 5)
    OPTIONAL MATCH (e1:Event)
    WHERE e1.category = e.category AND e1.eventId <> e.eventId
    WITH e, collect(DISTINCT e1) as category_events
    
    // 2. Events with same host (weight: 4)
    OPTIONAL MATCH (e)-[:HOSTED]->(host:User)-[:HOSTED]->(e2:Event)
    WHERE e2.eventId <> e.eventId
    WITH e, category_events, collect(DISTINCT e2) as host_events
    
    // 3. Events with same interests (weight: 4)
    OPTIONAL MATCH (e)-[:RELATES_TO_INTEREST]->(i:Interest)<-[:RELATES_TO_INTEREST]-(e3:Event)
    WHERE e3.eventId <> e.eventId
    WITH e, category_events, host_events, collect(DISTINCT e3) as interest_events
    
    // 4. Events that attract same people (weight: 3)
    OPTIONAL MATCH (e)-[:ATTRACTS_PEOPLE]->(p:Person)<-[:ATTRACTS_PEOPLE]-(e4:Event)
    WHERE e4.eventId <> e.eventId
    WITH e, category_events, host_events, interest_events, collect(DISTINCT e4) as people_events
    
    // 5. Events at same location (weight: 3)
    OPTIONAL MATCH (e5:Event)
    WHERE e5.location = e.location AND e5.eventId <> e.eventId
    WITH e, category_events, host_events, interest_events, people_events, collect(DISTINCT e5) as location_events
    
    // 6. Events attended by same people (weight: 3)
    OPTIONAL MATCH (e)-[:ATTENDED_EVENT]-(attendee:User)-[:ATTENDED_EVENT]->(e6:Event)
    WHERE e6.eventId <> e.eventId
    WITH e, category_events, host_events, interest_events, people_events, location_events, collect(DISTINCT e6) as attendee_events
    
    // 7. Events at same time of day (weight: 2)
    OPTIONAL MATCH (e)-[:BEST_TIME]->(t:Time)<-[:BEST_TIME]-(e7:Event)
    WHERE e7.eventId <> e.eventId
    WITH e, category_events, host_events, interest_events, people_events, location_events, attendee_events, collect(DISTINCT e7) as time_events
    
    // Combine all events and calculate scores
    WITH e, 
         category_events + host_events + interest_events + people_events + 
         location_events + attendee_events + time_events as all_events
    
    UNWIND all_events as similar_event
    WITH similar_event, e,
         // Calculate weighted score based on which list the event appears in
         CASE 
             WHEN similar_event IN category_events THEN 5
             WHEN similar_event IN host_events THEN 4
             WHEN similar_event IN interest_events THEN 4
             WHEN similar_event IN people_events THEN 3
             WHEN similar_event IN location_events THEN 3
             WHEN similar_event IN attendee_events THEN 3
             WHEN similar_event IN time_events THEN 2
             ELSE 1
         END as base_score
    
    // Add bonus for events happening soon
    WITH similar_event, e, base_score,
         CASE 
             WHEN similar_event.eventDate <= datetime() + duration('P30D') THEN 2  // Next 30 days
             WHEN similar_event.eventDate <= datetime() + duration('P60D') THEN 1  // Next 60 days
             ELSE 0
         END as time_bonus
    
    WITH similar_event, e, base_score + time_bonus as final_score
    
    RETURN similar_event.eventId as event_id,
           final_score as score
    ORDER BY final_score DESC
    LIMIT $limit
    """

    parameters = {"event_id": event_id, "limit": limit}

    graph_client = GraphClient()
    results = graph_client.run_query(query, parameters)
    graph_client.close()

    return [
        {
            "event_id": record["event_id"],
            "match_score": record["score"],
        }
        for record in results
    ]
