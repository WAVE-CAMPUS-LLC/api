# Social API - Crew Management Endpoints

This module provides API endpoints for managing crew-related functionality in the social platform.

## New Crew Endpoints

### 1. Get User Crews (Paginated)

**Endpoint:** `GET /waveYourCampusAPIFromOAK/social/get_user_crews_paginated`

**Description:** Retrieves all crews a user is a member of with pagination support to prevent slow load times with large crew lists.

**Parameters:**

-   `page` (int, optional): Page number (starts from 1, default: 1)
-   `page_size` (int, optional): Number of crews per page (max 50, default: 10)
-   `platform` (str, optional): Platform identifier for logging

**Authentication:** Required (via `caller_user_id`)

**Response:**

```json
{
	"crews": [
		{
			"crewId": "uuid-string",
			"name": "Crew Name",
			"member_count": 5
		}
	],
	"pagination": {
		"current_page": 1,
		"page_size": 10,
		"total_crews": 25,
		"total_pages": 3,
		"has_next": true,
		"has_previous": false
	}
}
```

### 2. Get Crew Details with Members

**Endpoint:** `GET /waveYourCampusAPIFromOAK/social/get_crew_details_with_members/{crew_id}`

**Description:** Retrieves comprehensive information about a specific crew including all members, shared events, and user membership status.

**Parameters:**

-   `crew_id` (UUID): The unique identifier of the crew
-   `platform` (str, optional): Platform identifier for logging

**Authentication:** Required (via `caller_user_id`)

**Response:**

```json
{
	"crew_details": {
		"crewId": "uuid-string",
		"name": "Crew Name",
		"bio": "Crew description",
		"created_at": "2024-01-01T00:00:00Z",
		"created_by": {
			"user_id": "uuid-string",
			"username": "creator#1234",
			"first_name": "John",
			"last_name": "Doe",
			"profile_photo": "url-to-photo"
		},
		"members": [
			{
				"user": {
					"user_id": "uuid-string",
					"username": "member#1234",
					"first_name": "Jane",
					"last_name": "Smith"
				},
				"profile": {
					"profile_photo": "url-to-photo"
				},
				"membership_details": {
					"joined_at": "2024-01-01T00:00:00Z",
					"is_admin": false
				}
			}
		],
		"member_count": 5,
		"shared_events": [
			{
				"event": {
					"eventId": "uuid-string",
					"title": "Event Title",
					"date": "2024-01-01T00:00:00Z",
					"header_photo": "url-to-photo"
				},
				"sender": {
					"username": "sender#1234",
					"first_name": "Sender",
					"last_name": "Name"
				},
				"shared_at": "2024-01-01T00:00:00Z"
			}
		],
		"user_is_member": true,
		"user_is_admin": false
	}
}
```

## Features

### Pagination Support

-   Both endpoints support pagination to handle large datasets efficiently
-   Configurable page sizes with reasonable limits
-   Pagination metadata included in responses

### Performance Optimizations

-   Database queries optimized with `select_related` and `prefetch_related`
-   Limited data fetching to prevent memory issues
-   Efficient filtering and sorting

### Error Handling

-   Comprehensive error handling with detailed logging
-   User-friendly error messages
-   Notification system integration for monitoring

### Security

-   Authentication required for all endpoints
-   User permission checks for crew membership
-   Input validation and sanitization

## Usage Examples

### Getting User's Crews (First Page)

```bash
GET /waveYourCampusAPIFromOAK/social/get_user_crews_paginated?page=1&page_size=10
```

### Getting Crew Details

```bash
GET /waveYourCampusAPIFromOAK/social/get_crew_details_with_members/123e4567-e89b-12d3-a456-426614174000
```

## Notes

-   The paginated endpoint returns up to 3 random member profile photos per crew for preview purposes
-   The detailed endpoint includes all crew members with their full profile information
-   Both endpoints check user membership status and admin privileges
-   Shared events are limited to 20 per crew to prevent performance issues
-   All timestamps are in ISO 8601 format
