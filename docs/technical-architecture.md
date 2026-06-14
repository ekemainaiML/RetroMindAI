# RetroMindAI — Technical Architecture

## 1. System Overview

RetroMindAI is a full-stack web application that assesses internal combustion engine (ICE) vehicles for EV retrofit feasibility. It ingests six standardised photographs of a vehicle (left/right profile, front/rear, engine bay, underbody), runs them through a multi-stage AI pipeline — vehicle classification, deviation detection, geometry extraction, and feasibility scoring — and produces a structured compliance report with cost estimates, battery placement recommendations, wiring guidance, and a 3D digital twin.

The system is composed of **eight Docker services** orchestrated via Docker Compose, a **React/Next.js frontend**, and a **Python/FastAPI backend** with Redis-backed worker queues.

---

## 2. High-Level Architecture

```
                               ┌──────────────────────────────────────────────────┐
                               │                   Caddy (reverse proxy)          │
                               │  Port 80/443 → TLS termination, routing          │
                               │  /api/* → backend-api:8000                       │
                               │  /*     → frontend:3000                          │
                               └──────────┬──────────────────┬────────────────────┘
                                          │                  │
                    ┌─────────────────────┘                  └─────────────────────┐
                    ▼                                                             ▼
        ┌───────────────────────┐                                  ┌───────────────────────┐
        │    Frontend (Next.js) │                                  │   Backend API (uvicorn)│
        │    Port 3000          │◄──── HTTP (REST) ───────────────►│   Port 8000            │
        │    TypeScript/React   │                                  │   FastAPI / Python     │
        │    Three.js (3D view) │                                  │   20+ endpoint modules │
        │    Tailwind CSS v4    │                                  └───────┬───────────────┘
        └───────────────────────┘                                          │
                                                                           │
                    ┌───────────────────────────────────────────────────────┼───────────────────────┐
                    │                       │                              │                       │
                    ▼                       ▼                              ▼                       ▼
        ┌───────────────────┐   ┌───────────────────┐          ┌───────────────────┐   ┌───────────────────┐
        │   PostgreSQL 16   │   │   Redis 7          │          │   Neo4j (graph)   │   │ FreeCAD Worker    │
        │   Port 5432       │   │   Port 6379        │          │   Port 7687/7474  │   │ Port 8100         │
        │   Primary store    │   │   RQ queue + cache │          │   Knowledge graph │   │ CAD STEP/STL gen  │
        └───────────────────┘   └───────────────────┘          └───────────────────┘   └───────────────────┘
                                                                                                    │
                                                                           ┌────────────────────────┘
                                                                           ▼
                                                                ┌───────────────────────┐
                                                                │   MailHog (dev only)  │
                                                                │   Port 1025 (SMTP)    │
                                                                │   Port 8025 (UI)      │
                                                                └───────────────────────┘

        ┌─────────────────────────────────────────────────────────────────────────────────────────┐
        │  Background Workers (separate container, same codebase)                                 │
        │  ┌─────────────────────┐  ┌─────────────────────┐  ┌────────────────────────────────┐  │
        │  │ backend-worker      │  │ training-scheduler  │  │ (same Dockerfile.worker)       │  │
        │  │ RQ consumer         │  │ Optuna/RLLib tasks  │  │                                │  │
        │  │ Assessment pipeline │  │ ML model training   │  │                                │  │
        │  └─────────────────────┘  └─────────────────────┘  └────────────────────────────────┘  │
        └─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Services Breakdown

### 3.1 PostgreSQL 16 — Primary Database

**Role:** Persistent relational store for all domain data.

**Tables (18+):**
- `workshops` — tenant workspaces with branding, tier, settings
- `intake` — image upload sessions (view_slots, quality_scores, attempts, enhanced_views, occluded_views, swap_detected)
- `jobs` — assessment pipeline runs (status, stages, result JSON, retry tracking)
- `users` — user accounts with JWT authentication
- `audit_logs` — immutable audit trail (request/response bodies, 90-day retention)
- `portal_sessions` — customer-facing shared report links (approve/reject workflow)
- `oem_*` — OEM manufacturer/model/spec tables (mounting points, routing paths)
- `batches` / `batch_jobs` — batch ZIP intake processing
- `billing_usage` — API usage metering (Stripe integration)
- `email_preferences` — per-workshop email notification settings
- `recommendation_feedback` — customer approval/rejection of recommendations

**Access:** Via SQLAlchemy 2.0 ORM (`core/models.py`), Alembic for migrations (18 linear versions).

**Port:** `5432` (internal), mapped to `5433` in dev to avoid host conflicts.

---

### 3.2 Redis 7 — Queue & Cache

**Role:** RQ (Redis Queue) job broker + lightweight cache.

**Queues:**
- `default` — assessment pipeline jobs (enqueued by intake endpoint)
- `training` — ML model training tasks (enqueued by training-scheduler)

**Usage:**
- Job queue for async assessment processing (worker picks up, runs 11 stages, writes result)
- Optional caching layer (poll cache TTL of 2 seconds)
- RQ dashboard metrics exposed via `/metrics` endpoint

**Port:** `6379`

---

### 3.3 Neo4j (Community) — Knowledge Graph

**Role:** Graph database storing vehicle assessment relationships for retrofit DNA matching.

**Schema:**
- Nodes represent individual vehicle assessments (vehicle type, dimensions, deviation profile)
- Edges represent similarity relationships (shared deviation parameters, delta thresholds)
- Queried via `cypher` to find the `N` most similar retrofits for a new assessment

**Integration:**
- Queried by the assessment worker after deviation detection completes
- Results feed the "Similar Retrofit Matches" section and the DnaGraph SVG component
- Accessed via the `neo4j` Python driver (`pip install neo4j`)

**Ports:** `7687` (Bolt protocol), `7474` (HTTP browser UI)

---

### 3.4 Backend API (FastAPI + Uvicorn)

**Role:** HTTP API server — the single entry point for all client interactions.

**Framework:** FastAPI (Python 3.12) with automatic OpenAPI docs at `/docs` and `/redoc`.

**Key endpoints (20+ routers under `api/v1/endpoints/`):**

| Router | Key Endpoints | Purpose |
|---|---|---|
| `intake.py` | `POST /intake`, `GET /intake/{id}`, `PUT /intake/{id}/views/{slot}`, `POST /intake/{id}/analyze` | Image upload, reupload, quality checks, kickoff assessment |
| `jobs.py` | `GET /jobs/{id}`, `POST /jobs/{id}/confirm`, `POST /jobs/{id}/confirm-timeout` | Job status polling, user confirmation with confidence override |
| `reports.py` | `GET /reports/{job_id}` | Generates structured compliance report (15 sections) |
| `reports.py` | `GET /reports/{job_id}/pdf` | Renders HTML → PDF report via WeasyPrint |
| `pdf_export.py` | | |
| `oem.py` | `GET /oem/search`, `GET /oem/manufacturers`, etc. | OEM model database search for reference specs |
| `auth.py` | `POST /auth/login`, `GET /auth/sso/*` | JWT + SSO authentication |
| `history.py` | `GET /history` | Paginated assessment history with filters |
| `analytics.py` | `GET /analytics/workshop` | Monthly aggregated stats (intakes, feasibility, deviation types) |
| `knowledge_graph.py` | `GET /knowledge-graph` | Full graph data for SVG force-directed visualization |
| `cad_export.py` | `GET /cad/export/{id}?format=step\|stl` | 3D model export via FreeCAD worker |
| `portal.py` | `POST /portal/share`, `GET /portal/sessions`, `GET /portal/{token}/status` | Customer portal link generation and approval workflow |
| `admin.py` | Workshop CRUD, user management, OEM data management, ML training triggers | Admin dashboard operations |
| `settings.py` | Workshop profile, branding, API key renewal, capability toggles | User settings |
| `batch.py` | `POST /batch/upload`, `GET /batch/{id}` | Batch ZIP processing |
| `compare.py` | `POST /compare` | Side-by-side comparison of two assessments |
| `metrics.py` | `GET /metrics` | Prometheus metrics endpoint |
| `events.py` | `GET /jobs/{job_id}/events` (SSE) | Server-Sent Events for real-time job progress |

**Authentication:**
- API keys (`X-API-Key` header) for programmatic access
- JWT tokens for web session authentication
- SSO providers: Google OAuth, Azure AD
- Demo key recovery on 401

**Middleware:**
- CORS (configured for frontend origin)
- Rate limiting (configurable, default 1000/minute)
- Request logging to audit trail
- Degradation detection (circuit breaker pattern)
- Error handling with structured JSON responses

---

### 3.5 Backend Worker (RQ Consumer)

**Role:** Processes assessment jobs asynchronously from the Redis queue.

**Process Model:**
- Single Python process (`workers/main.py`) running an RQ worker
- Listens on `default` queue
- Picks up jobs enqueued by the intake `POST /analyze` endpoint
- Runs the full assessment pipeline (11 stages)
- Writes results back to the `jobs.result` JSONB column

**Assessment Pipeline Stages (in order):**

```
1. Image validation + downscaling
2. Low-light detection → auto-enhancement (CLAHE)
3. Occlusion detection (std deviation check)
4. Vehicle classification (ONNX → PyTorch fallback → heuristic)
5. OEM identification (CLIP embeddings → cosine similarity)
6. Deviation detection (geometry extraction → OEM spec comparison)
7. 3D geometry extraction (dimensions, wheelbase, ground clearance)
8. Risk assessment (severity aggregation → system risk state)
9. Confidence scoring (weighted factors: quality, geometry, visibility, classification)
10. Recommendation generation (rule-based → LLM refinement)
11. Knowledge graph update (Neo4j node+edge creation)
```

**Each stage has:**
- Individual timeout (5–60 seconds depending on complexity)
- Degradation-aware skip logic (if a dependent service is down)
- Structured error handling with per-stage failure logging
- Progress reporting via Redis pub/sub → SSE to frontend

---

### 3.6 Training Scheduler

**Role:** Periodic background task for ML model training.

**Capabilities:**
- Hyperparameter optimisation via Optuna
- Reinforcement learning training via RLlib (Ray)
- ONNX model retraining from accumulated assessment data
- Triggered by admin UI or cron schedule

**Commands:**
- `python -m workers.training_scheduler` (default command in Dockerfile.worker override)
- Currently lightweight — runs Optuna trials with SQLite backend

---

### 3.7 FreeCAD Worker

**Role:** Generates STEP/STL 3D models from assessment geometry data.

**Architecture:**
- Standalone FastAPI service (`freecad-worker/worker.py`)
- Runs on Ubuntu 22.04 with FreeCAD installed
- Called by `backend-api` via HTTP POST to `/export`
- Receives assessment data (dimensions), returns binary STEP or STL file

**Model Construction:**
- Parametric box-based vehicle model (body + cabin fused as "Chassis")
- Dimensions extracted from `geometry_result.measurements`
- Exports via FreeCAD's `Part.export` (STEP) or `MeshPart.meshFromShape` (STL)

**Health check:** `GET /health` returns `{"status": "ok"}`
**Port:** `8100`

---

### 3.8 MailHog (Development Only)

**Role:** Email capture for development.

**Integration:**
- SMTP server at port `1025`
- Web UI at port `8025` (http://localhost:8025)
- Backend SMTP_HOST set to `mailhog` service name
- Catches all outgoing emails (password resets, portal invitations, notifications)
- No actual email delivery — all messages viewable in web UI

In production, MailHog is replaced by a real SMTP relay (configurable via env vars).

---

### 3.9 Frontend (Next.js + React + TypeScript)

**Framework:** Next.js 16 (App Router), React 19, TypeScript 5

**Pages (17 routes):**

| Route | Purpose |
|---|---|
| `/` | Home — New Assessment (upload 6 images, OEM search, analysis, results) |
| `/capture` | Field Capture — live camera with guides, blur detection, offline IndexedDB |
| `/batch` | Batch ZIP upload |
| `/batch/[id]` | Batch dashboard with per-vehicle status |
| `/history` | Assessment history table with multi-select comparison |
| `/analytics` | Workshop analytics (SVG charts) |
| `/compare` | Side-by-side assessment comparison |
| `/knowledge-graph` | Force-directed SVG graph of all assessments |
| `/reports/[id]` | Full compliance report with all 15 sections |
| `/view/[id]` | Standalone 3D digital twin viewer (Three.js, raw) |
| `/portal/view/[token]` | Customer-facing report view (approve/reject) |
| `/settings` | User/workshop settings, billing, API keys, branding |
| `/admin` | Admin dashboard (workshops, users, audits, OEM, ML training) |
| `/login`, `/signup`, `/auth`, `/auth/callback` | Authentication |
| `/api-health` | System health check |

**Key Libraries:**
- **Three.js** (`three@0.184`) — 3D digital twin (procedural rickshaw/car/motorcycle models, battery fitment, thermal zones, wiring routes, measurement tool)
- **Tailwind CSS v4** — styling via utility classes + CSS custom properties
- **React Context** — theme (dark/light), user/auth state
- **Raw Three.js** (not React Three Fiber) — `DigitalTwinSceneContent.tsx` manages scene, camera, raycaster, animations imperatively
- **QRCode** (`qrcode` library) — shareable 3D view links
- **IndexedDB** (`idb-keyval`) — offline capture queue

**State Management:**
- React Context for global state (theme, user)
- Local `useState` + `useCallback` + `useEffect` per page
- `localStorage` for persistence (API key, JWT, active job/intake IDs, branding cache)
- No Redux, Zustand, or external state library

**Real-Time Updates:**
- **SSE (Server-Sent Events)** — `EventSource` connection to `/jobs/{id}/events` with automatic fallback to polling
- **Polling fallback** — 2-second interval GET `/jobs/{id}` (used when SSE fails or is unavailable)
- **Polling on history page** — 10-second interval for live status updates

**3D Digital Twin (`lib/` files):**
- `three-setup.ts` — Scene, camera, renderer, OrbitControls, lighting
- `rickshaw-model.ts` — Procedural vehicle meshes (rickshaw, car, motorcycle) via BoxGeometry/CylinderGeometry
- `battery-fitment.ts` — Translucent battery box with clearance indicators
- `thermal-zones.ts` — Pulsing semi-transparent spheres with temperature-based colouring
- `wiring-routes.ts` — CatmullRomCurve3 tube geometries with waypoint markers
- `measurement-tool.ts` — Distance measurement with raycasted point placement
- `DigitalTwinSceneContent.tsx` — 722-line orchestrator component managing all sub-models, raycasting, view mode toggles, overlays

---

## 4. AI/ML Pipeline

### 4.1 Vehicle Classification

**Architecture:** Multi-strategy pattern with fallback chain.

```
                  ┌────────────────────────────┐
                  │     classify(image_paths)   │
                  └──────────┬─────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼               ▼
   ┌─────────────────┐ ┌──────────────┐ ┌──────────────┐
   │  PyTorch Runner  │ │  ONNX Runner │ │  Heuristic   │
   │  (mobilenet.pt)  │ │ (classifier. │ │ (rule-based) │
   │  GPU-capable     │ │  onnx)       │ │  fallback    │
   │  enable_pytorch  │ │  Default     │ │              │
   └────────┬─────────┘ └──────┬───────┘ └──────────────┘
            │                  │
            └────────┬─────────┘
                     ▼
           ┌─────────────────────┐
           │  CLASS_LABELS =     │
           │  three_wheeler,     │
           │  motorcycle,        │
           │  four_wheeler,      │
           │  unknown            │
           └─────────────────────┘
```

**Strategies:**
1. **PyTorch** (`mobilenet.pt`, ~4MB) — Enabled via `enable_pytorch` feature flag. CPU-only in Docker (CPU PyTorch index). Higher accuracy but slower.
2. **ONNX** (`vehicle_classifier.onnx`, ~75KB) — Default path. Faster inference, cross-platform. Runs via `onnxruntime`.
3. **Heuristic** — Rule-based fallback when no model is loaded. Uses image properties (size, colour distribution, aspect ratio) to guess vehicle type.

**Label mapping:** `["three_wheeler", "motorcycle", "four_wheeler", "unknown"]`

### 4.2 Image Preprocessing

**Downscaling** (`ai/downscale.py`):
- If image dimension > `image_max_dimension` (default 1920px), resize preserving aspect ratio
- Output path: `{original}_downscaled.{ext}`
- Uses OpenCV `INTER_AREA` interpolation

**Low-Light Detection** (`ai/classification/preprocess.py`):
- Converts to grayscale, computes mean brightness
- Threshold: `LOW_LIGHT_THRESHOLD` (40/255)
- If below threshold, triggers `auto_enhance()`

**Auto-Enhancement** (`ai/classification/preprocess.py`):
- CLAHE (Contrast Limited Adaptive Histogram Equalization) on LAB colour space
- clipLimit=3.0, tileGridSize=(8,8)
- Output path: `{original}_enhanced.{ext}` (or `{original}_downscaled_enhanced.{ext}` if downscaled first)
- Enhanced image replaces original for the classification pipeline

**Occlusion Detection** (`ai/classification/preprocess.py`):
- Computes standard deviation of pixel values
- Below `OCCLUSION_STD_THRESHOLD` (15) → flagged as occluded
- Coverage check via dark pixel ratio (pixels < 30/255)

### 4.3 OEM Identification

- Uses **OpenAI CLIP** (`clip_text_embeddings.pkl`, 3.3MB) for zero-shot vehicle type matching
- Vehicle images are encoded and compared against pre-computed text embeddings of OEM models
- Cosine similarity scoring → top-K OEM suggestions
- Requires `OPENAI_API_KEY` for CLIP API access (or uses local embedding lookup)

### 4.4 Deviation Detection

- Extracts geometric measurements from images (dimensions, panel gaps, structural alignment)
- Compares against OEM reference specifications from the `oem_*` tables
- Computes delta percentages per parameter
- Flags critical deviations (delamination, structural damage)
- Generates salvage potential score

### 4.5 Confidence & Risk Scoring

**Confidence Engine** (`core/confidence.py`):
- Weighted scoring: image quality (20%), geometry certainty (25%), classification confidence (25%), completeness (15%), deviation coverage (15%)
- `apply_safety_overrides()` — reduces confidence on swap detection, occlusion, or critical degradation

**Risk Assessment:**
- Groups deviations by severity (low/medium/high/critical)
- Computes `system_risk_state` (normal/caution/at_risk/critical)
- Feasibility scoring based on deviation count, severity, and salvage potential

### 4.6 Recommendation Generation

**Two-stage process:**
1. **Rule-based** — Template recommendations mapped to deviation types (e.g., "Corrosion in engine bay → replace mounting points")
2. **LLM refinement** (optional) — OpenAI GPT refines descriptions, adds context, estimates costs
   - Requires `OPENAI_API_KEY` and `enable_generative_design` flag

**Recommendation categories:**
- `structural`, `electrical`, `battery_placement`, `safety`, `compliance`, `general`

**Priority mapping:** `high → "essential"`, `medium → "recommended"`, `low → "optional"`

---

## 5. Data Flow: End-to-End Assessment

```
USER                     FRONTEND                    BACKEND API              WORKER            DATABASES
 │                         │                            │                      │                   │
 │  Upload 6 photos ──────►│                            │                      │                   │
 │                         │  POST /intake (multipart) ─►│                      │                   │
 │                         │                            │  Store paths          │                   │
 │                         │                            │  Compute qlty scores  │                   │
 │                         │                            │  Save to DB ──────────┼─────────────────►│ PostgreSQL
 │                         │                            │                      │                   │
 │                         │◄─── { intake_id } ─────────┤                      │                   │
 │                         │                            │                      │                   │
 │                         │  POST /intake/{id}/analyze►│                      │                   │
 │                         │                            │  Create Job ──────────┼─────────────────►│ PostgreSQL
 │                         │                            │  Enqueue RQ ──────────┼─────────────────►│ Redis
 │                         │                            │                      │                   │
 │  Poll progress ◄────────┤  SSE /events OR poll ──────┤                      │                   │
 │                         │                            │                      │                   │
 │                         │                            │              Worker picks up job         │
 │                         │                            │                      │                   │
 │                         │                            │              ┌─────────────────────┐      │
 │                         │                            │        1.    │ Downscale images    │      │
 │                         │                            │        2.    │ Detect low light    │      │
 │                         │                            │        3.    │ Auto-enhance        │      │
 │                         │                            │        4.    │ Check occlusion     │      │
 │                         │                            │        5.    │ Classify vehicle ───┼─────►│ ONNX/PyTorch
 │                         │                            │        6.    │ Identify OEM ───────┼─────►│ CLIP embeddings
 │                         │                            │        7.    │ Detect deviations   │      │
 │                         │                            │        8.    │ Geometry extraction │      │
 │                         │                            │        9.    │ Assess risk         │      │
 │                         │                            │        10.   │ Score confidence    │      │
 │                         │                            │        11.   │ Gen recommendations │      │
 │                         │                            │              └─────────────────────┘      │
 │                         │                            │                      │                   │
 │                         │                            │         Write result ──┼─────────────────►│ PostgreSQL
 │                         │                            │                      │                   │
 │                         │                            │         Update Neo4j ──┼─────────────────►│ Neo4j
 │                         │                            │                      │                   │
 │  View results ◄─────────┤  GET /jobs/{id} ───────────►│                      │                   │
 │                         │                            │  Read result ────────┼─────────────────►│ PostgreSQL
 │                         │◄─── { assessment_data } ───┤                      │                   │
 │                         │                            │                      │                   │
 │  View report ◄──────────┤  GET /reports/{job_id} ────►│                      │                   │
 │                         │                            │  Build 15 sections ──┼─────────────────►│ PostgreSQL
 │                         │◄─── { compliance_report } ─┤                      │                   │
 │                         │                            │                      │                   │
 │  Confirm/override       │  POST /jobs/{id}/confirm ──►│                      │                   │
 │                         │                            │  Update confidence    │                   │
 │                         │                            │  Recompute compliance │                   │
 │                         │                            │  Save ───────────────┼─────────────────►│ PostgreSQL
 │                         │                            │  Send email (portal) ─┼─────────────────►│ MailHog/SMTP
 │                         │                            │                      │                   │
 │  Export CAD ◄───────────┤  GET /cad/export/{id} ─────►│  POST /export ──────►│ FreeCAD Worker   │
 │                         │◄────── STEP/STL binary ─────┤◄──── binary ─────────┤                   │
 │                         │                            │                      │                   │
 │  Share with customer    │  POST /portal/share ───────►│                      │                   │
 │                         │                            │  Create session ─────┼─────────────────►│ PostgreSQL
 │                         │◄─── { portal_url } ────────┤                      │                   │
```

---

## 6. Integration Points

### 6.1 REST API (HTTP/JSON)

Primary communication channel between frontend and backend. All requests include `X-API-Key` header for authentication. Response format is always JSON (except for CAD exports which return binary, and the `/metrics` endpoint which returns Prometheus text format).

### 6.2 Server-Sent Events (SSE)

**Endpoint:** `GET /jobs/{job_id}/events?token={api_key}`

**Flow:**
1. Backend publishes progress events to Redis pub/sub channel `job:{job_id}:events`
2. SSE endpoint subscribes to the channel and forwards events to the frontend
3. Each event is a JSON blob: `{ event, job_id, status, current_stage, progress_pct, completed_stages }`
4. Terminal events (`completed`, `failed`, `cancelled`) close the connection
5. Frontend falls back to 2-second polling if SSE fails after 5 retries

**Why SSE over WebSocket:**
- Simpler protocol (HTTP-based, no upgrade handshake)
- Automatic reconnection built into `EventSource` API
- Works through all HTTP proxies and load balancers
- Sufficient for unidirectional server→client progress updates

### 6.3 Redis Queue (RQ)

**Enqueue:**
```python
from redis import Redis
from rq import Queue

redis = Redis.from_url(settings.redis_url)
queue = Queue("default", connection=redis)
queue.enqueue(assessment_pipeline, job_id=str(job.id))
```

**Dequeue:**
Worker process runs `python -m workers.main` which starts an RQ worker listening on the `default` queue. The worker:
1. Pops jobs from the queue (blocking pop)
2. Executes `assessment_pipeline(job_id)` with the full assessment logic
3. Commits results to PostgreSQL
4. Publishes progress events to Redis pub/sub
5. Handles timeouts, degradations, and failures per stage

### 6.4 PostgreSQL (SQLAlchemy 2.0)

- ORM models in `core/models.py` (18 tables)
- JSONB columns for flexible schema (view_slots, attempts, quality_scores, job result, etc.)
- Alembic for schema migrations (18 linear versions, CI-validated)
- UUID primary keys across all tables
- Health check via `pg_isready` in Docker Compose

### 6.5 Neo4j (Cypher)

- Graph database for retrofit DNA similarity matching
- Nodes: assessments (vehicle type, dimensions, deviation profile)
- Edges: similarity relationships (weighted by shared deviation parameters)
- Queried after deviation detection to find top-K similar retrofits
- Forward-only integration — no writes from the frontend

### 6.6 FreeCAD (HTTP)

- Dedicated worker container running FreeCAD + FastAPI
- Called by `cad_export.py` endpoint on demand
- Blocks until model generation completes (typically <2 seconds)
- Returns binary file stream (STEP or STL MIME types)

### 6.7 ML Models (ONNX / PyTorch / CLIP)

- ONNX: `onnxruntime` Python package, CPU inference, ~75KB model
- PyTorch: `torch` CPU-only (PyTorch CPU index), ~4MB model, feature-flagged
- CLIP embeddings: Pre-computed `.pkl` file (~3.3MB), loaded at startup
- All models bundled in the Docker image (`backend/ai/models/`)

---

## 7. Monitoring & Observability

### 7.1 Prometheus Metrics

**Endpoint:** `GET /api/v1/metrics` (Prometheus text format)

**Exported metrics (via `prometheus_client`):**
- `http_requests_total` — counter by method, endpoint, status
- `http_request_duration_seconds` — histogram by method, endpoint
- `demo_assessments_total` — counter
- `jobs_created_total` / `jobs_completed_total` — counters
- **RQ queue depth** — gauge (via RQ dashboard plugin)
- **Circuit breaker state** — gauge by service name (postgres, redis, neo4j, freecad)
- **Backup status** — gauge

**Pre-configured alerts (24/7):**
- Error rate > 5% (critical, 5m window)
- P95 latency > 5s (warning)
- Queue depth > 100 (warning), > 500 (critical)
- Circuit breaker open → critical
- Disk space < 15% (warning), < 5% (critical)
- Service down > 1m (critical)
- Rate limit hits > 10/s (warning)

### 7.2 Grafana Dashboard

**Single dashboard:** "RetroMind AI — Platform Overview" (UID: `retromind-platform`)

**Panels:** Request rate, error rate, latency (P50/P95/P99), queue depth, circuit breakers, DB connections, rate limit hits, health checks, active workshops, backup age

**Refresh:** 30 seconds, datasource: Prometheus

### 7.3 Sentry (Production)

- Error tracking via `SENTRY_DSN` env var
- Only active when `ENVIRONMENT=production`

---

## 8. Infrastructure & DevOps

### 8.1 Docker Compose (Dev)

```
docker compose up -d
```

Starts all 8 services with:
- Hot-reload code mounts (./backend:/app for API & worker)
- Debug ports exposed (5433, 6379, 7687, 7474, 8025, 8100)
- No TLS — HTTP directly on port 8000
- MailHog for email capture
- Default credentials for all services

### 8.2 Production Deployment

**Target:** Oracle Cloud Infrastructure Ampere A1 (ARM64, 4 OCPU, 24GB RAM)

**Deployment flow:**
1. Manual trigger via GitHub Actions (`workflow_dispatch` with "deploy" confirmation)
2. SSH into VM via `appleboy/ssh-action`
3. `git pull origin main`
4. Copy `.env.prod` from secure location
5. `docker compose -f docker-compose.prod.yml build --pull && up -d`
6. `docker system prune -af`
7. Smoke test frontend + API health endpoint

**Production differences from dev:**
- Caddy reverse proxy with TLS (Let's Encrypt via ACME)
- No MailHog (real SMTP relay required)
- No exposed ports except 80/443 (Caddy)
- Persistent volumes for uploads (`app_uploads`)
- ARM64-native builds (`--pull` ensures fresh base images)
- `.env.prod` with real secrets (DB passwords, JWT secret, OCI credentials)

### 8.3 Caddy Configuration

**`infra/caddy/Caddyfile`:**
```caddy
{$DOMAIN} {
    route /api/* {
        reverse_proxy backend-api:8000
    }
    reverse_proxy frontend:3000
    header * Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    header * X-Content-Type-Options "nosniff"
    header * X-Frame-Options "DENY"
    header * Referrer-Policy "strict-origin-when-cross-origin"
}
```

### 8.4 CI/CD Pipeline

**`.github/workflows/ci.yml`** (runs on PR to `main`):
1. **lint** — Ruff (Python linter + formatter)
2. **typecheck** — Mypy on `api/` and `core/`
3. **migration-test** — Alembic upgrade → downgrade → upgrade (validates reversibility)
4. **dependency-scan** — `pip-audit` + `npm audit`
5. **test** — Pytest unit tests (Postgres service container)
6. **frontend-build** — `npm ci && npm run build`

---

## 9. Security Architecture

### 9.1 Authentication

**Two-factor auth strategy:**
- **API Keys** (`rm_` prefix, 42-char hex) — primary auth for API calls, stored in `X-API-Key` header
- **JWT Tokens** — web session auth (stored in localStorage, sent as `Authorization: Bearer <jwt>`)
- **SSO Providers** — Google OAuth 2.0, Azure AD (configurable via env vars)

### 9.2 Authorization

- **Workspace isolation** — All data scoped to `workshop_id` (UUID)
- **Admin role** — Separate `ADMIN_API_KEY` for admin dashboard
- **Audit trail** — All mutations logged to `audit_logs` table with 90-day retention

### 9.3 Data Protection

- **Encryption at rest** — PostgreSQL data (depends on hosting)
- **Encryption in transit** — TLS via Caddy in production
- **Upload isolation** — Per-workshop upload directories (`{UPLOAD_DIR}/{workshop_id}/`)
- **No secrets in code** — All credentials via environment variables
- **Rate limiting** — Configurable, default 1000 requests/minute

### 9.4 Customer Portal Security

- Token-based access (random UUID per session)
- Read-only customer view (approve/reject only)
- Token expiry (configurable via `portal_token_expiry_hours`, default 72h)

---

## 10. Feature Flags & Degradation Management

### 10.1 Feature Flags

All advanced features default to `False` and are runtime-overridable:

| Flag | Purpose |
|---|---|
| `enable_optuna` | Hyperparameter optimization |
| `enable_pytorch` | PyTorch inference (vs ONNX-only) |
| `enable_rl_recommendations` | RL-based recommendation refinement |
| `enable_generative_design` | LLM-based recommendation enrichment |
| `enable_cad_export` | STEP/STL CAD export |

Flags can be toggled at runtime via admin UI (uses `_feature_overrides` class variable) without code deployment.

### 10.2 Degradation Manager (`core/degradation.py`)

Three-tier degradation system:
- **Tier 1:** Non-critical service unavailable (continue with cached/default data)
- **Tier 2:** Partial assessment pipeline failure (skip failed stages, continue with subset)
- **Tier 3:** Critical infrastructure failure (mark assessment as "inconclusive")

Integrated with circuit breaker pattern (tracked via Prometheus).

---

## 11. Database Schema Highlights

### 11.1 Intake (core/models.py)

```python
class Intake(Base):
    __tablename__ = "intake"
    id = Column(UUID, primary_key=True)
    workshop_id = Column(UUID, ForeignKey("workshops.id"))
    view_slots = Column(JSONB)       # {"left_side_profile": "/uploads/...", ...}
    attempts = Column(JSONB)          # {"left_side_profile": 3, ...}
    quality_scores = Column(JSONB)    # {"left_side_profile": 0.87, ...}
    low_quality_views = Column(JSONB) # ["left_side_profile"]
    enhanced_views = Column(JSONB)    # ["underbody", "engine_bay"]
    occluded_views = Column(JSONB)    # ["rear_view"]
    swap_detected = Column(Boolean)
    status = Column(String)
    oem_model_id = Column(UUID, ForeignKey("oem_models.id"))
```

### 11.2 Job (core/models.py)

```python
class Job(Base):
    __tablename__ = "jobs"
    id = Column(UUID, primary_key=True)
    intake_id = Column(UUID, ForeignKey("intake.id"))
    status = Column(String)           # pending, running, completed, failed
    current_stage = Column(String)
    completed_stages = Column(JSONB)
    result = Column(JSONB)            # Full assessment result (all stages)
    retry_count = Column(Integer)
    error_message = Column(Text)
```

---

## 12. Language & Framework Summary

| Component | Language | Framework / Runtime | Key Libraries |
|---|---|---|---|
| Backend API | Python 3.12 | FastAPI, Uvicorn | SQLAlchemy 2.0, Alembic, Pydantic, OpenCV, onnxruntime, PyTorch, RQ, httpx |
| Backend Worker | Python 3.12 | RQ (Redis Queue) | Same as API + Neo4j driver, OpenAI SDK |
| Training Scheduler | Python 3.12 | RQ | Optuna, Ray/RLlib, PyTorch |
| Frontend | TypeScript 5 | Next.js 16 (App Router), React 19 | Three.js, Tailwind CSS v4, qrcode, idb-keyval |
| FreeCAD Worker | Python 3.10 | FastAPI, Uvicorn | FreeCAD Python API |
| Database | SQL | PostgreSQL 16 | — |
| Graph DB | Cypher | Neo4j Community | — |
| Queue/Cache | — | Redis 7 | — |
| Proxy | — | Caddy 2 (with ACME) | — |
| SSO | — | Google OAuth, Azure AD | — |
| CI/CD | — | GitHub Actions | Ruff, Mypy, Pytest, pip-audit |
| Infrastructure | — | Docker Compose, Terraform (OCI) | — |
| Monitoring | — | Prometheus, Grafana, Sentry | — |

---

## 13. Performance Characteristics

| Operation | Typical Latency | Bottleneck |
|---|---|---|
| Image upload (6 photos) | 2–10 seconds | Network / disk I/O |
| Vehicle classification (ONNX) | 200–800ms | CPU inference |
| Vehicle classification (PyTorch) | 1–3 seconds | CPU inference |
| Deviation detection | 3–10 seconds | Image processing + DB lookup |
| Full assessment pipeline | 20–60 seconds | Sequential stage execution |
| PDF report generation | 3–8 seconds | WeasyPrint HTML→PDF |
| CAD export (STEP/STL) | 1–3 seconds | FreeCAD model generation |
| SSE event delivery | <100ms | Redis pub/sub |
| API response (cached poll) | <50ms | Redis / PostgreSQL |

---

## 14. Development Workflow

### Prerequisites
- Docker Desktop (or Docker Engine + Compose plugin)
- 8GB+ RAM allocated to Docker
- Node.js 20+ (for frontend dev outside Docker)

### Quick Start
```bash
# 1. Start all services
docker compose up -d

# 2. Run database migrations
docker compose exec backend-api alembic upgrade head

# 3. Open frontend
open http://localhost:3000

# 4. API docs
open http://localhost:8000/docs

# 5. MailHog UI
open http://localhost:8025

# 6. Neo4j Browser
open http://localhost:7474
```

### Testing
```bash
# Backend unit tests (CI equivalent)
docker compose exec backend-api python -m pytest tests/unit/ -q

# Backend all tests (including slow)
docker compose exec backend-api python -m pytest tests/ -q --runslow

# Frontend lint
cd frontend && npm run lint

# Frontend type check
cd frontend && npx tsc --noEmit
```

### Common Tasks
```bash
# Create migration
docker compose exec backend-api alembic revision --autogenerate -m "description"

# Apply migrations
docker compose exec backend-api alembic upgrade head

# View RQ queue
docker compose exec redis redis-cli --raw LLEN rq:queue:default

# View logs
docker compose logs -f backend-worker

# Rebuild backend
docker compose up -d --build backend-api backend-worker
```
