# Tier 3 — Production Hardening & Scale

## Guiding Principles
- Everything in `docker compose up` must still work after each item.
- No breaking API changes to v1 routes; any new routes go under `/api/v2/` if incompatible.
- 237+ tests must continue to pass.

---

## T3.1 — Workshop Self-Service Portal

**What:** Replace the hardcoded demo workshop with a real registration flow. Workshops sign up, get their own API key, and manage their assessments.

**Sub-items:**
- `POST /api/v1/auth/register` — name + email → creates workshop + returns raw API key
- `POST /api/v1/auth/renew` — invalidate old key, issue new one (requires current key)
- `GET /api/v1/workshop/profile` — name, key prefix, created_at, assessment count
- Frontend `/settings` page — shows API key prefix, "Renew Key" button with confirmation
- Migrate demo workshop to a "guest" tier (auto-renewed on restart, visible in settings)

**Why:** Without this, every user shares the same demo key. Real workshops need isolated keys.

**Acceptance:** Register → receive key → use key immediately. Renew → old key stops working, new key works. Settings page shows key info.

---

## T3.2 — Production CI/CD Deploy (Oracle Cloud Free Tier)

**What:** Deploy to an Oracle Cloud Free Tier VM on merge to `main`. The VM runs all services via Docker Compose behind an nginx reverse proxy with automated Let's Encrypt SSL.

**Architecture:**

```
Oracle VM.Standard.ARM (4 OCPU, 24 GB RAM — Always Free)
├── nginx (port 80/443, Let's Encrypt SSL)
│   ├── /api/* → backend-api:8000
│   └── /*     → frontend:3000 (Next.js standalone)
├── Docker Compose services:
│   ├── frontend (Next.js standalone, Docker multi-stage build)
│   ├── backend-api (FastAPI via Dockerfile.prod)
│   ├── backend-worker (RQ worker)
│   ├── postgres:16
│   ├── redis:7
│   ├── neo4j:community
│   └── certbot (auto-renew)
└── Persistent volumes: postgres_data, neo4j_data, upload_data, certbot
```

**Sub-items:**
- GitHub Actions `deploy.yml` — trigger on push to `main`
  - Job 1: Lint + type-check + test (reuses `ci.yml`)
  - Job 2: SSH into Oracle VM → `git pull` → `docker compose build` → `up -d`
- `docker-compose.prod.yml` — production compose file (no `--reload`, no volume mounts for code, nginx proxy, certbot)
- `frontend/Dockerfile` — multi-stage build (node:20-alpine builder → runner)
- `backend/Dockerfile.prod` — production uvicorn server without `--reload`
- `infra/nginx/nginx.conf` — reverse proxy with HTTP→HTTPS redirect, certbot challenge location
- `scripts/setup-oracle-vm.sh` — one-time VM provisioning (Docker, git clone, .env, SSL cert, first deploy)
- Required GitHub secrets: `ORACLE_HOST`, `ORACLE_USER`, `ORACLE_SSH_KEY`, `ORACLE_DEPLOY_PATH`

**Key differences from local dev (`docker-compose.yml`):**
- Nginx sidecar handles SSL termination and reverse proxy
- Frontend runs as a containerized Next.js standalone server (not Next.js dev server on host)
- No volume mounts for live code reload — images are self-contained
- `ENVIRONMENT=production` env var set
- Persistent volumes for uploads, databases, and SSL certs
- All services use `restart: always`

**Why:** Manual deploys are error-prone. Oracle Cloud Free Tier provides 4 ARM cores and 24 GB RAM at no cost — enough to run the full stack including Neo4j. No PaaS lock-in.

**Acceptance:** Merge PR → CI passes → GitHub Actions SSHes into Oracle VM → `git pull && docker compose build && up -d`. Production site accessible at `https://<domain>` with valid SSL. `docker compose -f docker-compose.prod.yml ps` shows all services healthy.

---

## T3.3 — Real Image E2E Test Suite

**What:** Replace synthetic test images with real vehicle photos and run the full pipeline against them.

**Sub-items:**
- Curate a test set of 5–10 real vehicle images (3-wheeler, motorcycle, car, modified frames)
- Store them in `backend/tests/fixtures/images/` (git-lfs or small enough for git)
- Write integration tests that:
  - Upload images → create intake → analyze → wait for job → assert stages completed
  - Assert classification matches expected type
  - Assert deviations detected for known-modified vehicles
  - Assert compliance state matches expected
- Add `pytest --runslow` marker; CI runs fast tests only, nightly runs full suite

**Why:** Synthetic images don't stress the real OpenCV pipeline. Real images catch edge cases.

**Acceptance:** `pytest --runslow` completes all pipeline tests against real images. At least one modified vehicle test detects deviations. CI fast suite still completes in < 2 min.

---

## T3.4 — Performance & Load Testing

**Status:** Implemented

**What:** Characterize system limits and fix bottlenecks before they hit production.

**Sub-items:**
- `tests/locustfile.py` — 4 scenarios (health, poll, upload+analyze, get intake) with realistic weights
- Bottlenecks addressed:
  - **DB connection pool sizing** — QueuePool(10, overflow=20), pre-ping, recycle 3600s (locked in `core/database.py`)
  - **RQ worker concurrency** — `WORKER_CONCURRENCY` env var (default 1, set to 2–4 on Oracle VM); spawns N multiprocessing workers
  - **Image processing** — `ai/downscale.py` downscales to `IMAGE_MAX_DIMENSION` (default 1920px) before OpenCV pipeline; `INTER_AREA` interpolation
  - **Polling overhead** — `poll_cache_ttl=2s` Redis cache on `GET /jobs/{id}` for terminal-status jobs; graceful Redis fallback
- `docs/load-testing.md` — usage, before/after estimates, commands

**Why:** Without load testing, the first production spike will be the first time we see bottlenecks.

**Acceptance:** Locust report shows < 500ms p95 for poll endpoints at 50 req/s. Expected throughput: ~200 polls/sec (was ~20), 2–4 concurrent assessments (was 1).

---

## T3.5 — Admin Dashboard

**What:** Internal admin panel for monitoring system health, viewing audit logs, and managing workshops.

**Sub-items:**
- `GET /api/v1/admin/workshops` — list all workshops (admin API key only)
- `GET /api/v1/admin/audit-logs` — paginated audit log viewer
- `GET /api/v1/admin/metrics` — dashboard JSON (aggregated metrics)
- Frontend `/admin` page:
  - Workshop list with key prefix, status, assessment count
  - Audit log table with filter by workshop, method, status
  - Real-time poll health from `/api/v1/health`
  - Degradation timeline chart
- Admin API key seeded via env var `ADMIN_API_KEY` at startup

**Acceptance:** Visit `/admin` → see active workshops, audit log entries, health status. Filter audit logs by workshop.

---

## T3.6 — Real-Time Job Updates (SSE)

**What:** Add optional SSE endpoint for job progress, deprecating polling for modern clients.

**Sub-items:**
- `GET /api/v1/jobs/{id}/events` — SSE stream emitting `job.progress` events on stage changes
- RQ worker publishes progress to Redis pub/sub on each stage completion
- SSE endpoint subscribes to Redis channel, forwards to client
- Frontend: optional SSE hook (`useJobSSE`) falls back to polling if SSE fails or not supported
- No breaking change — polling continues to work unchanged

**Why:** 2s polling is wasteful at scale. SSE is a minor protocol addition that dramatically reduces server load.

**Acceptance:** 10 concurrent SSE connections → zero polling requests. Client-side fallback to polling works seamlessly. SSE disconnected → auto-reconnect with last-event-id.

---

## T3.7 — Workshop Analytics & Usage Insights

**What:** Give workshops visibility into their own usage patterns and assessment quality.

**Sub-items:**
- `GET /api/v1/workshop/stats` — monthly aggregation:
  - Total assessments, pass/fail rates
  - Average confidence score by month
  - Most common deviation types
  - Average processing time
- Frontend `/analytics` page with charts:
  - Monthly assessment bar chart
  - Confidence trend line
  - Deviation type pie chart
- Store aggregated stats in a materialized view or cache (computed on demand, cached 1h)

**Why:** Workshops need to see their own data to trust and adopt the system.

**Acceptance:** After 10+ assessments, `/workshop/stats` returns meaningful aggregations. Frontend charts render with correct data.

---

## T3.8 — API v2 Planning (Incremental)

**What:** Lay groundwork for v2 without shipping it yet.

**Sub-items:**
- Define v2 route prefix `/api/v2/` in router
- Move one proof-of-concept endpoint to v2 (e.g., `/api/v2/jobs/{id}` with Response Model v2 that includes paginated telemetry)
- Add `Accept-Version` header negotiation (optional, still use prefix)
- Document v2 migration guide in `docs/api-v2.md`

**Why:** v1 routes are frozen. v2 lets us iterate on API design without breaking existing clients.

**Acceptance:** `GET /api/v2/jobs/{id}` returns the same data as v1 plus new `telemetry[]` array. No v1 routes changed.

---

## Summary

| Item | Effort | Impact | Risk |
|------|--------|--------|------|
| T3.1 Workshop Portal | Medium | High | Low |
| T3.2 CI/CD Deploy | Medium | Critical | Medium |
| T3.3 Real Image Tests | Medium | High | Low |
| T3.4 Load Testing | Medium | Medium | Low |
| T3.5 Admin Dashboard | Large | High | Low |
| T3.6 SSE Job Updates | Large | Medium | Medium |
| T3.7 Workshop Analytics | Medium | Medium | Low |
| T3.8 API v2 Prep | Small | Low | Low |

**Recommended starting point:** T3.2 (CI/CD) + T3.3 (real image tests) — these ship value and catch regressions before deeper work.
