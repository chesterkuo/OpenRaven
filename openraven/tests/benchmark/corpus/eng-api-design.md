# REST API Design Guidelines

## Version Control
All APIs must be versioned using URL path versioning: `/api/v1/resource`. Breaking changes require a new major version. Non-breaking additions (new optional fields) can be added to existing versions.

## Authentication
We use OAuth 2.0 with JWT bearer tokens. All API endpoints require authentication except `/health` and `/api/v1/auth/login`. Tokens expire after 1 hour. Refresh tokens are valid for 30 days.

## Rate Limiting
- Standard tier: 100 requests/minute per API key
- Premium tier: 1000 requests/minute per API key
- Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

## Error Handling
All errors follow RFC 7807 Problem Details format:
```json
{
  "type": "https://api.example.com/errors/validation",
  "title": "Validation Error",
  "status": 422,
  "detail": "Email field is required",
  "instance": "/api/v1/users"
}
```

## Pagination
List endpoints use cursor-based pagination with `after` and `limit` parameters. Default page size is 20, maximum is 100. Response includes `next_cursor` and `has_more` fields.

## Naming Conventions
- Endpoints use kebab-case: `/api/v1/user-profiles`
- JSON fields use snake_case: `created_at`, `user_id`
- Query parameters use snake_case: `?sort_by=created_at&order=desc`
