# Event Recommendation System Implementation

## Overview

The event recommendation system has been enhanced to automatically handle users with and without college affiliations. The system now intelligently detects college information from user profiles and adjusts recommendations accordingly.

## Key Features

### 1. Automatic College Detection

-   **API Endpoint**: `/api/walle/suggest/events`
-   **Auto-detection**: Automatically detects college from user profile if not provided
-   **Fallback handling**: Gracefully handles users without college affiliations
-   **Optional parameter**: `college_name` is now optional in the API

### 2. Enhanced Neo4j Queries

-   **Conditional college filtering**: College-based recommendations only apply when college is specified
-   **Multi-factor scoring**: Considers friends, mutuals, preferences, and college context
-   **Time-based bonuses**: Recent events get higher scores
-   **Preference matching**: Uses UserPreferences model for personalized recommendations

### 3. API Response Enhancements

-   **College context indicator**: `has_college_context` field shows if college was detected
-   **Auto-detection flag**: `college_auto_detected` indicates if college was auto-detected
-   **Detailed event info**: Returns event details with match scores

## Implementation Details

### API Endpoint Changes

```python
@router.get("/suggest/events")
async def suggest_events(
    request: Request,
    current_user_id: int = Depends(get_current_user),
    college_name: Optional[str] = Query(None, description="User's college name (optional - will auto-detect from profile)"),
    limit: int = Query(10, description="Maximum number of event suggestions"),
    platform: Optional[str] = None,
):
```

**Key Changes:**

-   `college_name` is now optional (`Optional[str]`)
-   Auto-detection logic added to extract college from user profile
-   Fallback to `None` for users without college
-   Enhanced response with context indicators

### Neo4j Query Enhancements

The event recommendation query now includes conditional college filtering:

```cypher
// 4. Events hosted by users from same college (weight: 3) - only if college is specified
OPTIONAL MATCH (e4:Event)<-[:HOSTED]-(host:User)
WHERE $college_name IS NOT NULL AND host.college = $college_name

// 5. Events where other college members are going (weight: 2) - only if college is specified
OPTIONAL MATCH (e5:Event)<-[:RSVP]-(college_user:User)
WHERE $college_name IS NOT NULL AND college_user.college = $college_name AND college_user.user_id <> $user_id
```

**Scoring System:**

-   Friends going to events: **5 points**
-   Friends who attended similar events: **4 points**
-   Events matching preferences: **4 points**
-   Mutual friends going to events: **3 points**
-   College-hosted events: **3 points** (only if college specified)
-   Interest-based events: **3 points**
-   People-matching events: **3 points**
-   College RSVP events: **2 points** (only if college specified)
-   Time-preference events: **2 points**
-   Time bonus (next 7 days): **+2 points**
-   Time bonus (next 14 days): **+1 point**

### Function Signature Updates

```python
def get_event_recommendations_for_user(
    user_id: str,
    college_name: Optional[str] = None,
    limit: int = 10
):
```

**Changes:**

-   Added `Optional` import from typing
-   Made `college_name` optional with default `None`
-   Enhanced error handling for edge cases

## Usage Examples

### 1. API Usage

**With college specified:**

```bash
GET /api/walle/suggest/events?college_name=Stanford%20University&limit=10
```

**Auto-detection (no college parameter):**

```bash
GET /api/walle/suggest/events?limit=10
```

### 2. Response Format

```json
{
	"user_id": "12345",
	"user_name": "john_doe",
	"college_name": "Stanford University",
	"college_auto_detected": true,
	"has_college_context": true,
	"event_recommendations": [
		{
			"event_id": "event-123",
			"title": "Campus Social Mixer",
			"event_date": "2024-01-15T18:00:00Z",
			"location": "Student Center",
			"description": "Meet new people and make connections",
			"match_score": 8.5
		}
	],
	"limit": 10,
	"platform": "web"
}
```

### 3. Testing

**Django Management Command:**

```bash
python manage.py test_event_recommendations
python manage.py test_event_recommendations --user-id 12345 --limit 5
```

**Direct Function Testing:**

```python
from socialGraphManagement.recommendations.event.event import get_event_recommendations_for_user

# Test with college
recommendations = get_event_recommendations_for_user("user123", "Stanford University", 5)

# Test without college (auto-detection)
recommendations = get_event_recommendations_for_user("user123", None, 5)
```

## Error Handling

### 1. User Not Found

-   Returns 404 with appropriate error message
-   Logs error for debugging

### 2. College Detection Failures

-   Gracefully falls back to `None` for college
-   Continues with non-college-based recommendations
-   Logs detection errors for monitoring

### 3. Neo4j Connection Issues

-   Handles connection failures gracefully
-   Returns empty recommendations list
-   Logs connection errors

## Performance Considerations

### 1. Caching

-   Consider implementing Redis caching for frequent queries
-   Cache user profile data to avoid repeated database calls

### 2. Query Optimization

-   Neo4j queries use indexes on `user_id` and `college` fields
-   Limit parameter prevents excessive result sets
-   Time-based filtering reduces data processing

### 3. Database Connections

-   Proper connection management in GraphClient
-   Connection pooling for high-traffic scenarios

## Future Enhancements

### 1. Machine Learning Integration

-   Use user behavior data to improve scoring algorithms
-   Implement collaborative filtering for better recommendations

### 2. Real-time Updates

-   WebSocket integration for live recommendation updates
-   Event-based triggers for recommendation refreshes

### 3. Advanced Filtering

-   Category-based filtering
-   Location-based recommendations
-   Price range filtering

### 4. A/B Testing

-   Implement different recommendation algorithms
-   Track user engagement with recommendations
-   Optimize based on user feedback

## Monitoring and Analytics

### 1. Key Metrics

-   Recommendation click-through rates
-   User engagement with recommended events
-   College detection success rates
-   Query performance metrics

### 2. Logging

-   Structured logging for all API calls
-   Error tracking and alerting
-   Performance monitoring

### 3. Analytics Dashboard

-   Real-time recommendation metrics
-   User behavior analysis
-   System performance monitoring

## Security Considerations

### 1. Authentication

-   All endpoints require user authentication
-   User ID validation prevents unauthorized access

### 2. Data Privacy

-   No sensitive user data exposed in recommendations
-   College information handled securely
-   GDPR compliance for user data

### 3. Rate Limiting

-   Implement rate limiting for API endpoints
-   Prevent abuse of recommendation system

## Conclusion

The enhanced event recommendation system now provides a seamless experience for both college-affiliated and non-college users. The automatic college detection feature ensures that users get relevant recommendations regardless of their college status, while the enhanced scoring system provides more accurate and personalized event suggestions.

The implementation is robust, scalable, and ready for production use with comprehensive error handling, testing capabilities, and monitoring support.
