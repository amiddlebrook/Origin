# Analytics API Documentation

This document provides detailed information about the Analytics API endpoints available in the Origin application.

## Table of Contents
- [Overview](#overview)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [Track Activity](#track-activity)
  - [Track Search](#track-search)
  - [Track Content Interaction](#track-content-interaction)
  - [Get Activity Analytics](#get-activity-analytics)
  - [Get Search Analytics](#get-search-analytics)
  - [Get Content Analytics](#get-content-analytics)
- [Analytics Models](#analytics-models)

## Overview
The Analytics API provides endpoints for tracking user activities, search queries, and content interactions, as well as retrieving analytics data. This data can be used to understand user behavior, content popularity, and system usage patterns.

## Authentication
All analytics endpoints require authentication. Include a valid JWT token in the `Authorization` header:

```
Authorization: Bearer <your_jwt_token>
```

## Endpoints

### Track Activity
Track a user activity event.

**Endpoint:** `POST /analytics/activity`

**Request Body:**
```json
{
  "activity_type": "string",
  "activity_data": {},
  "ip_address": "string",
  "user_agent": "string"
}
```

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "activity_type": "string",
  "activity_data": {},
  "ip_address": "string",
  "user_agent": "string",
  "created_at": "2025-08-11T17:00:00Z"
}
```

### Track Search
Track a search query.

**Endpoint:** `POST /analytics/search`

**Request Body:**
```json
{
  "query": "string",
  "filters": {},
  "result_count": 0,
  "ip_address": "string",
  "user_agent": "string"
}
```

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "query": "string",
  "filters": {},
  "result_count": 0,
  "ip_address": "string",
  "user_agent": "string",
  "created_at": "2025-08-11T17:00:00Z"
}
```

### Track Content Interaction
Track a user's interaction with content.

**Endpoint:** `POST /analytics/interaction`

**Request Body:**
```json
{
  "content_type": "string",
  "content_id": 1,
  "interaction_type": "view",
  "duration_seconds": 0,
  "metadata": {}
}
```

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "content_type": "string",
  "content_id": 1,
  "interaction_type": "view",
  "duration_seconds": 0,
  "metadata": {},
  "created_at": "2025-08-11T17:00:00Z"
}
```

### Get Activity Analytics
Get analytics about user activities.

**Endpoint:** `GET /analytics/activities`

**Query Parameters:**
- `start_date`: Start date (ISO format, default: 30 days ago)
- `end_date`: End date (ISO format, default: now)
- `activity_type`: Filter by activity type
- `user_id`: Filter by user ID (admin only)

**Response:**
```json
{
  "total_activities": 0,
  "activities_by_type": {},
  "activities_over_time": [],
  "top_users": []
}
```

### Get Search Analytics
Get analytics about search queries.

**Endpoint:** `GET /analytics/searches`

**Query Parameters:**
- `start_date`: Start date (ISO format, default: 30 days ago)
- `end_date`: End date (ISO format, default: now)
- `user_id`: Filter by user ID (admin only)

**Response:**
```json
{
  "total_searches": 0,
  "popular_queries": [],
  "searches_over_time": [],
  "zero_result_queries": []
}
```

### Get Content Analytics
Get analytics about content interactions.

**Endpoint:** `GET /analytics/content`

**Query Parameters:**
- `start_date`: Start date (ISO format, default: 30 days ago)
- `end_date`: End date (ISO format, default: now)
- `content_type`: Filter by content type
- `content_id`: Filter by content ID
- `user_id`: Filter by user ID (admin only)

**Response:**
```json
{
  "total_interactions": 0,
  "interactions_by_type": {},
  "popular_content": [],
  "interactions_over_time": []
}
```

## Analytics Models

### User Activity
Tracks user activities in the system.

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Unique identifier |
| user_id | integer | ID of the user who performed the activity |
| activity_type | string | Type of activity (e.g., 'login', 'logout', 'content_create') |
| activity_data | object | Additional data about the activity |
| ip_address | string | IP address of the user |
| user_agent | string | User agent string |
| created_at | datetime | When the activity was recorded |

### Search Query
Tracks search queries performed by users.

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Unique identifier |
| user_id | integer | ID of the user who performed the search |
| query | string | The search query |
| filters | object | Any filters applied to the search |
| result_count | integer | Number of results returned |
| ip_address | string | IP address of the user |
| user_agent | string | User agent string |
| created_at | datetime | When the search was performed |

### Content Interaction
Tracks user interactions with content.

| Field | Type | Description |
|-------|------|-------------|
| id | integer | Unique identifier |
| user_id | integer | ID of the user who interacted with the content |
| content_type | string | Type of content (e.g., 'story', 'research') |
| content_id | integer | ID of the content |
| interaction_type | string | Type of interaction (e.g., 'view', 'like', 'share') |
| duration_seconds | integer | How long the interaction lasted (if applicable) |
| metadata | object | Additional data about the interaction |
| created_at | datetime | When the interaction occurred |
