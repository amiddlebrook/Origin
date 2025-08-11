# Bulk Operations and Rate Limiting

This document provides an overview of the bulk operations and rate limiting features in the Origin application.

## Table of Contents
- [Bulk Operations](#bulk-operations)
  - [Research Operations](#research-operations)
  - [Story Operations](#story-operations)
  - [Oral History Operations](#oral-history-operations)
  - [Workspace Operations](#workspace-operations)
- [Rate Limiting](#rate-limiting)
  - [Default Rate Limits](#default-rate-limits)
  - [Endpoint-Specific Rate Limits](#endpoint-specific-rate-limits)
  - [Rate Limit Headers](#rate-limit-headers)

## Bulk Operations

The bulk operations API allows you to perform create, update, and delete operations on multiple items at once. This is particularly useful for batch processing and data migration scenarios.

### Research Operations

#### Bulk Create Research

```http
POST /bulk/research/create?skip_duplicates=true
```

**Request Body:**
```json
[
  {
    "title": "Research 1",
    "description": "Description 1",
    "content": "Content 1",
    "is_public": true
  },
  {
    "title": "Research 2",
    "description": "Description 2",
    "content": "Content 2",
    "is_public": false
  }
]
```

**Response:**
```json
{
  "total": 2,
  "created": 2,
  "skipped": 0,
  "errors": []
}
```

#### Bulk Update Research

```http
PUT /bulk/research/update
```

**Request Body:**
```json
[
  {
    "id": 1,
    "title": "Updated Research 1",
    "is_public": false
  },
  {
    "id": 2,
    "description": "Updated description"
  }
]
```

**Response:**
```json
{
  "total": 2,
  "updated": 2,
  "not_found": 0,
  "errors": []
}
```

#### Bulk Delete Research

```http
POST /bulk/research/delete
```

**Request Body:**
```json
[1, 2, 3]
```

**Response:**
```json
{
  "total": 3,
  "deleted": 3,
  "not_found": 0,
  "errors": []
}
```

### Story Operations

Similar endpoints are available for name stories:

- `POST /bulk/stories/create` - Bulk create stories
- `PUT /bulk/stories/update` - Bulk update stories
- `POST /bulk/stories/delete` - Bulk delete stories

### Oral History Operations

Similar endpoints are available for oral histories:

- `POST /bulk/oral-histories/create` - Bulk create oral histories
- `PUT /bulk/oral-histories/update` - Bulk update oral histories
- `POST /bulk/oral-histories/delete` - Bulk delete oral histories

### Workspace Operations

#### Bulk Add to Workspace

```http
POST /bulk/workspaces/{workspace_id}/resources/add
```

**Request Body:**
```json
[
  {
    "resource_type": "research",
    "resource_id": 1
  },
  {
    "resource_type": "story",
    "resource_id": 42
  }
]
```

**Response:**
```json
{
  "total": 2,
  "added": 2,
  "skipped": 0,
  "errors": []
}
```

#### Bulk Remove from Workspace

```http
POST /bulk/workspaces/{workspace_id}/resources/remove
```

**Request Body:**
```json
[
  {
    "resource_type": "research",
    "resource_id": 1
  }
]
```

**Response:**
```json
{
  "total": 1,
  "removed": 1,
  "not_found": 0,
  "errors": []
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse and ensure fair usage. Rate limits are applied per client (user or IP) and per endpoint.

### Default Rate Limits

- **Default**: 60 requests per minute
- **Authentication**: 10 requests per minute
- **Search**: 30 requests per minute
- **Uploads**: 10 requests per minute

### Endpoint-Specific Rate Limits

| Endpoint | Method | Limit |
|----------|--------|-------|
| `/auth/register` | POST | 5 per hour |
| `/auth/login` | POST | 10 per minute |
| `/auth/forgot-password` | POST | 3 per hour |
| `/auth/reset-password` | POST | 5 per hour |
| `/stories/` | POST | 30 per minute |
| `/oral/upload` | POST | 10 per minute |
| `/media/upload` | POST | 20 per minute |

### Rate Limit Headers

When a rate limit is approached or exceeded, the API includes the following headers in the response:

- `X-RateLimit-Limit`: The maximum number of requests allowed in the time window
- `X-RateLimit-Remaining`: The number of requests remaining in the current window
- `X-RateLimit-Reset`: The time at which the current rate limit window resets (UNIX timestamp)
- `X-RateLimit-Reset-After`: The number of seconds until the rate limit resets
- `Retry-After`: The number of seconds until the client can make another request (only included when rate limited)

### Example Rate Limited Response

When a client exceeds the rate limit, they will receive a `429 Too Many Requests` response:

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 60
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1620000000
X-RateLimit-Reset-After: 60

{
  "detail": "Rate limit exceeded. Try again in 60 seconds.",
  "retry_after": 60,
  "limit": 60,
  "window_seconds": 60
}
```

## Best Practices

1. **Bulk Operations**:
   - Use bulk operations for importing or updating large datasets
   - Set `skip_duplicates=true` when you want to avoid duplicate entries
   - Handle errors in the response to identify any failed operations

2. **Rate Limiting**:
   - Implement exponential backoff when you receive a 429 response
   - Cache responses when possible to reduce API calls
   - Use the `X-RateLimit-*` headers to implement client-side rate limiting

3. **Error Handling**:
   - Always check the `errors` array in bulk operation responses
   - Implement retry logic for transient errors
   - Log rate limit warnings to identify potential issues in your application
