# API v2 Migration Guide

## Overview

API v2 (`/api/v2/`) is an incremental evolution of RetroMind AI's REST API. v1 routes are frozen — no breaking changes will be made. v2 allows iterating on API design without breaking existing clients.

## Version Strategy

- **Primary routing**: URL prefix (`/api/v1/` vs `/api/v2/`)
- **Header negotiation** (optional): Clients may send `Accept-Version: 2.0` header. When present, the response includes `X-API-Version: 2.0` and `X-API-Latest: /api/v2/` headers. A warning is logged if a v2 client hits a v1 endpoint.

## Current v2 Endpoints

### `GET /api/v2/jobs/{job_id}` — Job Details with Telemetry

Extends v1 `GET /api/v1/jobs/{job_id}` with a `telemetry` block:

```json
{
  "job_id": "...",
  "status": "completed",
  ...standard v1 fields...,
  "telemetry": {
    "total_requests": 142,
    "overall_avg_duration_ms": 234.5,
    "route_breakdown": [
      {"method": "GET", "path": "/api/v1/jobs/{id}", "request_count": 45, "avg_duration_ms": 12.3},
      {"method": "POST", "path": "/api/v1/intake", "request_count": 12, "avg_duration_ms": 890.1}
    ]
  }
}
```

**Differences from v1:**
| Field | v1 | v2 |
|-------|----|----|
| `telemetry` | Not present | Object with `total_requests`, `overall_avg_duration_ms`, `route_breakdown` |
| `job_id` | `str` | `str` (unchanged) |
| Response Model | `JobResponse` | `JobResponseV2` |

**Telemetry scope**: Last 24 hours of audit logs for the authenticated workshop.

## Migration Path

### For existing v1 clients:
No action needed. v1 routes are stable and will remain available.

### To adopt v2:
1. Change URL prefix from `/api/v1/` to `/api/v2/`
2. Optionally send `Accept-Version: 2.0` header to receive version headers in responses
3. Handle the new `telemetry` field in job responses (ignore if not needed)

## Future v2 Plans

- Paginated intake history with cursor-based pagination
- Bulk job status endpoint (`POST /api/v2/jobs/batch`)
- Standardized error format (`{ "error": { "code": "...", "message": "...", "details": {} } }`)
- Rate limit headers (`X-RateLimit-Remaining`, `X-RateLimit-Reset`)
- Webhook registration for job completion events

## Deprecation Policy

v1 endpoints will receive security patches only after v2 reaches feature parity. At minimum, v1 will be supported for 6 months after a v2 equivalent is marked stable.
