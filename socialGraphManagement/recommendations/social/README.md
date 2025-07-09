# Friend Recommendation System

This module provides a comprehensive friend recommendation system that leverages Neo4j graph database to suggest potential friends for users based on various factors like shared interests, events attended, mutual friends, and more.

## Features

-   **Graph-based recommendations**: Uses Neo4j to analyze user relationships and similarities
-   **Multi-factor scoring**: Considers shared interests, events, mutual friends, and preferences
-   **AI-powered personalization**: Uses OpenAI GPT to generate personalized recommendation messages
-   **Notification integration**: Sends recommendations through the existing notification system
-   **Batch processing**: Can send recommendations to all users at once
-   **Error handling**: Robust error handling and logging

## How It Works

### 1. Recommendation Algorithm

The system uses a sophisticated Neo4j query that considers:

-   **Shared Interests**: Users who have similar interests (weight: 3x)
-   **Shared Events**: Users who attended the same events (weight: 3x)
-   **Shared Times**: Users with similar preferred times (weight: 2x)
-   **Shared People**: Users who want to meet the same people (weight: 2x)
-   **Vibe Match**: Users with similar vibes (weight: 2x)
-   **Mutual Friends**: Users with mutual friends (weight: 1x)

### 2. Personalization

The system uses OpenAI GPT to generate personalized, college-style messages that encourage users to check out their suggested friends.

### 3. Notification System

Recommendations are sent through the existing notification system, ensuring consistency with the rest of the application.

## Usage

### Basic Usage

```python
from socialGraphManagement.recommendations.social.friend import (
    get_friend_recommendations,
    suggest_friends_for_user,
    send_hourly_friend_recommendations
)

# Get recommendations for a specific user
recommendations = get_friend_recommendations("user_id", limit=5)

# Generate a personalized message for a user
message = suggest_friends_for_user("user_id", "username")

# Send recommendations to all users
result = send_hourly_friend_recommendations()
```

### Django Management Command

Send recommendations to all users:

```bash
# Send to all users
python manage.py send_friend_recommendations

# Dry run (see what would be sent without actually sending)
python manage.py send_friend_recommendations --dry-run

# Limit to first 10 users (for testing)
python manage.py send_friend_recommendations --limit 10
```

### Testing

Run the test script to verify the system works:

```bash
python socialGraphManagement/recommendations/social/test_friend_recommendations.py
```

## Configuration

### Required Settings

Make sure these settings are configured in your Django settings:

```python
# Neo4j Configuration
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

# OpenAI Configuration
COLLEGE_OPENAI_API_KEY = "your-openai-api-key"
```

### Graph Database Schema

The system expects the following nodes and relationships in Neo4j:

**Nodes:**

-   `User` with properties: `user_id`, `vibe`
-   `Interest` with properties: `name`
-   `Event` with properties: `event_id`, `title`
-   `Time` with properties: `name`
-   `Person` with properties: `name`

**Relationships:**

-   `(User)-[:INTERESTED_IN]->(Interest)`
-   `(User)-[:ATTENDED_EVENT]->(Event)`
-   `(User)-[:PREFERRED_TIME]->(Time)`
-   `(User)-[:WANTS_TO_MEET]->(Person)`
-   `(User)-[:FRIEND]-(User)`
-   `(User)-[:REQUESTED]->(User)`

## API Functions

### `get_friend_recommendations(user_id: str, limit: int = 5)`

Returns a list of recommended users with scores.

**Parameters:**

-   `user_id`: The user ID to get recommendations for
-   `limit`: Maximum number of recommendations to return

**Returns:**

```python
[
    {"user_id": "user123", "score": 15},
    {"user_id": "user456", "score": 12},
    ...
]
```

### `suggest_friends_for_user(user_id: str, user_name: str, limit: int = 5) -> str`

Generates a personalized message suggesting friends for a user.

**Parameters:**

-   `user_id`: The user ID
-   `user_name`: The user's display name
-   `limit`: Maximum number of recommendations to consider

**Returns:**
A personalized message string.

### `send_hourly_friend_recommendations()`

Sends friend recommendations to all active users.

**Returns:**

```python
{
    "successful_notifications": 150,
    "failed_notifications": 5,
    "total_users": 155
}
```

## Scheduling

To run this automatically, you can set up a scheduled task using Celery Beat or cron:

### Celery Beat Example

```python
# settings.py
CELERY_BEAT_SCHEDULE = {
    'send-friend-recommendations': {
        'task': 'socialGraphManagement.tasks.send_friend_recommendations',
        'schedule': crontab(hour=10, minute=0),  # Daily at 10 AM
    },
}
```

### Cron Example

```bash
# Send recommendations daily at 10 AM
0 10 * * * cd /path/to/project && python manage.py send_friend_recommendations
```

## Error Handling

The system includes comprehensive error handling:

-   **Graph database errors**: Logged and handled gracefully
-   **OpenAI API errors**: Fallback to generic messages
-   **User not found**: Logged and skipped
-   **Notification errors**: Logged and tracked

## Monitoring

The system provides detailed logging for monitoring:

-   Recommendation generation success/failure
-   Notification delivery status
-   Performance metrics
-   Error tracking

Check the logs for entries from `socialGraphManagement.recommendations.social.friend` to monitor the system.

## Performance Considerations

-   **Batch processing**: Process users in batches for large user bases
-   **Caching**: Consider caching recommendations for frequently accessed users
-   **Rate limiting**: Respect OpenAI API rate limits
-   **Database optimization**: Ensure Neo4j indexes are properly configured

## Troubleshooting

### Common Issues

1. **No recommendations returned**: Check if users exist in the graph database
2. **OpenAI errors**: Verify API key and quota
3. **Neo4j connection errors**: Check database connectivity and credentials
4. **Notification failures**: Verify user exists and notification system is working

### Debug Mode

Enable debug logging to see detailed information:

```python
import logging
logging.getLogger('socialGraphManagement.recommendations.social.friend').setLevel(logging.DEBUG)
```
