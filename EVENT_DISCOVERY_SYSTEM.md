# Event Discovery System

## Overview

The Event Discovery System provides personalized event recommendations with pagination, prioritizing events based on user preferences, social connections, and college context. The system loads events gradually as users make requests, providing a smooth browsing experience.

## Key Features

### 1. Personalized Event Discovery

-   **Multi-factor scoring**: Considers friends, preferences, interests, and college context
-   **Time-based prioritization**: Recent events get higher scores
-   **College-aware**: Adjusts recommendations based on user's college affiliation
-   **Social graph integration**: Uses Neo4j to analyze social connections

### 2. Pagination System

-   **Configurable page size**: Default 3 events per page, max 20
-   **Progressive loading**: Loads more events as users browse
-   **Efficient caching**: Fetches more events upfront to ensure smooth pagination
-   **Metadata included**: Provides pagination info for UI implementation

### 3. API Endpoint

-   **Endpoint**: `/api/walle/discover/events`
-   **Authentication**: Required (uses current user)
-   **Auto-detection**: Automatically detects college from user profile
-   **Flexible parameters**: Customizable page size and college context

## Implementation Details

### Scoring Algorithm

The system uses a weighted scoring algorithm with the following factors:

1. **Friends attending this event** (Weight: 5)

    - Direct social connection to the event
    - Highest priority for social engagement

2. **Friends who attended similar events** (Weight: 4)

    - Indirect social validation
    - Based on event category matching

3. **College context** (Weight: 3)

    - Events hosted by users from same college
    - Only applies if user has college affiliation

4. **College members attending** (Weight: 2)

    - Other college members RSVP'd to the event
    - Only applies if user has college affiliation

5. **Event matches user preferences** (Weight: 4)

    - Time preferences, people to meet, interests
    - Direct preference matching

6. **User's interests match event** (Weight: 3)

    - Interest-based recommendations
    - Uses user's declared interests

7. **Event time matches user preferences** (Weight: 2)

    - Time-based preference matching
    - Considers user's preferred times

8. **Event attracts people user wants to meet** (Weight: 3)
    - People-based recommendations
    - Matches user's "people to meet" preferences

### Time Bonuses

-   **Next 7 days**: +3 points
-   **Next 14 days**: +2 points
-   **Next 30 days**: +1 point

### API Response Format

```json
{
	"user_id": "12345",
	"user_name": "john_doe",
	"college_name": "Stanford University",
	"college_auto_detected": true,
	"has_college_context": true,
	"events": [
		{
			"event_id": "event-uuid-1",
			"title": "Campus Social Mixer",
			"header_photo": "/media/event_photos/mixer_header.jpg",
			"match_score": 15.5
		},
		{
			"event_id": "event-uuid-2",
			"title": "Tech Meetup",
			"header_photo": "/media/event_photos/tech_meetup.jpg",
			"match_score": 12.3
		}
	],
	"pagination": {
		"current_page": 1,
		"page_size": 3,
		"total_events": 45,
		"total_pages": 15,
		"has_next": true,
		"has_previous": false,
		"next_page": 2,
		"previous_page": null
	},
	"platform": "web"
}
```

## Usage Examples

### 1. Basic Usage (First Page)

```bash
GET /api/walle/discover/events?page=1&page_size=3
```

**Response**: First 3 events with pagination metadata

### 2. Load More Events

```bash
GET /api/walle/discover/events?page=2&page_size=3
```

**Response**: Next 3 events (events 4-6)

### 3. Custom Page Size

```bash
GET /api/walle/discover/events?page=1&page_size=5
```

**Response**: First 5 events

### 4. With College Context

```bash
GET /api/walle/discover/events?page=1&college_name=Stanford%20University
```

**Response**: Events prioritized for Stanford University students

### 5. Auto-Detection (No College Parameter)

```bash
GET /api/walle/discover/events?page=1
```

**Response**: Events with college auto-detected from user profile

## Frontend Integration

### 1. Initial Load

```javascript
// Load first page of events
const response = await fetch("/api/walle/discover/events?page=1&page_size=3");
const data = await response.json();

// Display events
data.events.forEach((event) => {
	displayEvent(event);
});

// Store pagination info
const pagination = data.pagination;
```

### 2. Load More Events

```javascript
// Load next page when user scrolls or clicks "Load More"
if (pagination.has_next) {
	const nextPage = await fetch(
		`/api/walle/discover/events?page=${pagination.next_page}&page_size=3`
	);
	const nextData = await nextPage.json();

	// Append new events
	nextData.events.forEach((event) => {
		displayEvent(event);
	});

	// Update pagination
	pagination = nextData.pagination;
}
```

### 3. Infinite Scroll Implementation

```javascript
// Detect when user reaches bottom
window.addEventListener("scroll", () => {
	if (
		window.innerHeight + window.scrollY >=
		document.body.offsetHeight - 1000
	) {
		loadMoreEvents();
	}
});

async function loadMoreEvents() {
	if (pagination.has_next && !isLoading) {
		isLoading = true;
		// Load next page...
		isLoading = false;
	}
}
```

## Performance Considerations

### 1. Efficient Querying

-   **Batch fetching**: Gets more events upfront to ensure smooth pagination
-   **Indexed queries**: Uses database indexes for fast retrieval
-   **Caching strategy**: Consider Redis caching for frequently accessed data

### 2. Database Optimization

-   **Selective fields**: Only fetches required event data (title, header_photo, event_id)
-   **Connection pooling**: Efficient database connection management
-   **Query optimization**: Neo4j queries optimized for performance

### 3. Scalability

-   **Pagination limits**: Maximum 20 events per page to prevent overload
-   **Async processing**: All database operations wrapped in async context
-   **Error handling**: Graceful degradation for missing data

## Error Handling

### 1. User Not Found

```json
{
	"detail": "User with ID 12345 not found"
}
```

### 2. Invalid Parameters

```json
{
	"detail": "Page number must be greater than 0"
}
```

### 3. Database Errors

```json
{
	"detail": "Error generating event discovery: Connection timeout"
}
```

## Monitoring and Analytics

### 1. Key Metrics

-   **Discovery engagement**: How many events users view
-   **Pagination usage**: How often users load more events
-   **College detection success**: Success rate of auto-detection
-   **Performance metrics**: Response times and query performance

### 2. Logging

-   **Structured logging**: All API calls logged with context
-   **Error tracking**: Detailed error logs for debugging
-   **Performance monitoring**: Query execution times

### 3. Analytics Dashboard

-   **Real-time metrics**: Live discovery usage statistics
-   **User behavior**: How users interact with discovery
-   **Performance insights**: System performance trends

## Future Enhancements

### 1. Advanced Filtering

-   **Category filtering**: Filter by event categories
-   **Date range**: Filter by event dates
-   **Location-based**: Filter by event location
-   **Price filtering**: Filter by ticket prices

### 2. Machine Learning

-   **Behavioral scoring**: Learn from user interactions
-   **Collaborative filtering**: Use similar users' preferences
-   **A/B testing**: Test different scoring algorithms

### 3. Real-time Updates

-   **WebSocket integration**: Live event updates
-   **Push notifications**: New event alerts
-   **Dynamic scoring**: Real-time score updates

### 4. Enhanced Personalization

-   **Seasonal adjustments**: Holiday and seasonal preferences
-   **Mood-based**: Consider user's current context
-   **Social trends**: Popular events in user's network

## Security Considerations

### 1. Authentication

-   **Required authentication**: All endpoints require user login
-   **User validation**: Ensures users can only access their own data
-   **Rate limiting**: Prevents abuse of discovery system

### 2. Data Privacy

-   **Minimal data exposure**: Only necessary event data returned
-   **College privacy**: College information handled securely
-   **GDPR compliance**: User data protection compliance

### 3. Input Validation

-   **Parameter validation**: All query parameters validated
-   **SQL injection prevention**: Proper parameter binding
-   **XSS protection**: Sanitized output

## Conclusion

The Event Discovery System provides a robust, scalable solution for personalized event recommendations with efficient pagination. The system balances performance with personalization, ensuring users get relevant events while maintaining fast response times.

The implementation is production-ready with comprehensive error handling, monitoring capabilities, and security considerations. The system can be easily extended with additional features and optimizations as needed.
