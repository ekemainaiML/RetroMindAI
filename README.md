# RetroMind AI — EV Retrofit Intelligence System

An end-to-end EV retrofit assessment platform for workshops. Users upload vehicle images and receive AI-powered recommendations for electric conversion, including battery placement, motor selection, wiring routing, structural analysis, and cost estimation.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+
- Python 3.12+ (optional — backend runs in Docker)

### 1. Start Backend Services

```bash
docker compose build
docker compose up -d
docker compose ps
```

On first startup the backend automatically runs Alembic migrations and seeds the demo workshop, OEM data, and CLIP embeddings.

```bash
# Get your demo API key
docker compose logs backend-api | grep "full API key"
# or
curl http://localhost:8000/api/v1/setup/demo-key
```

### 2. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Navigate to `http://localhost:3000/auth` and click **"Use Demo Key"** to fetch the key from the running backend, or log in via **Sign In** / **Sign Up**.

### 3. Access the App

| Service        | URL                              |
|----------------|----------------------------------|
| Frontend       | `http://localhost:3000`          |
| API docs       | `http://localhost:8000/docs`     |
| FreeCAD worker | `http://localhost:8100/docs`     |
| Neo4j Browser  | `http://localhost:7474`          |

### 4. Rebuild After Code Changes

```bash
# Backend Python changes
docker compose build backend-api && docker compose up -d backend-api

# FreeCAD worker changes
docker compose build freecad-worker && docker compose up -d freecad-worker

# Frontend: hot-reloads automatically (Next.js dev server)
```

## Technology Stack

| Component       | Technology                                    |
|-----------------|-----------------------------------------------|
| Frontend        | Next.js 16 (App Router), Tailwind CSS 4, TypeScript |
| API             | FastAPI (Python 3.12)                         |
| Database        | PostgreSQL 16 (SQLAlchemy ORM, Alembic)       |
| Cache / Queue   | Redis 7 + RQ (background workers)             |
| Graph           | Neo4j (knowledge graph)                       |
| Object Storage  | S3-compatible (MinIO / R2 / OCI Object Storage) |
| Mail            | MailHog (dev) / SendGrid, SES, SMTP (prod)    |
| SSO             | Google OAuth, Microsoft Azure AD              |
| Reverse Proxy   | Caddy (auto TLS)                              |

## Core Features

| Feature                      | Description                                          | Status     |
|------------------------------|------------------------------------------------------|------------|
| Confidence scoring           | Custom `ConfidenceEngine` with weighted factors      | ✅ Active  |
| Deviation detection          | OpenCV circle/Hough detection + geometry analysis    | ✅ Active  |
| Battery zone optimization    | Template-based zone matcher                          | ✅ Active  |
| Wiring route planning        | Template-based path router                           | ✅ Active  |
| Report generation            | 13-section compliance report builder                 | ✅ Active  |
| OEM data models              | SQLAlchemy + Alembic (Phase 1-2)                     | ✅ Active  |
| **Enterprise Features**      |                                                      |            |
| PDF export                   | WeasyPrint-based PDF report generation               | ✅ Active  |
| White-labeling               | Custom logo, brand colors, custom domain             | ✅ Active  |
| Customer portal              | Token-based customer approval portal                 | ✅ Active  |
| Batch operations             | ZIP upload for multi-vehicle fleet assessment        | ✅ Active  |
| Mobile field capture         | Camera UI with 6-view guidance, offline queue        | ✅ Active  |
| Email notifications          | Configurable SMTP, per-event preferences             | ✅ Active  |
| SSO (Google / Azure AD)      | OAuth-based single sign-on                           | ✅ Active  |
| Subscription billing         | Stripe integration with tiered plans                 | ✅ Active  |
| Usage metering               | Per-workshop usage tracking with tier enforcement    | ✅ Active  |
| Audit trail                  | Before/after state logging for all mutations         | ✅ Active  |
| Circuit breakers             | Graceful degradation on downstream failure           | ✅ Active  |
| API key rotation             | Expiry dates, IP-based breach detection              | ✅ Active  |
| Rate limiting per tier       | Configurable rate limits with 429 responses          | ✅ Active  |

## Optional Phases (feature-flag-gated, off by default)

| Phase | Capability                       | Dependencies                    | Flag                       |
|-------|----------------------------------|---------------------------------|----------------------------|
| P0.5  | Hyperparameter optimization      | `optuna>=4.0`                   | `enable_optuna`            |
| P1    | PyTorch CNN classifier           | `torch`, `torchvision`          | `enable_pytorch`           |
| P2    | RLlib adaptive recommendations   | `ray[rllib]`                    | `enable_rl_recommendations`|
| P3    | Generative AI refinement         | `openai>=1.0` / `anthropic`     | `enable_generative_design` |
| P4    | FreeCAD CAD export (STEP/STL)    | `apt: freecad` (Ubuntu ARM64)   | `enable_cad_export`        |
| P5    | Continuous learning pipeline     | (uses P1 deps)                  | (auto via scheduler)       |

Install optional dependency groups:
```bash
pip install ".[optuna]"      # Phase 0.5
pip install ".[torch]"       # Phase 1
pip install ".[rllib]"       # Phase 2
pip install ".[genai]"       # Phase 3
pip install ".[all]"         # All optional
```

Start optional Docker services:
```bash
docker compose --profile freecad up   # Phase 4 FreeCAD worker
```

## Project Structure

```
├── frontend/               # Next.js 16 (App Router)
│   └── src/
│       ├── app/            # Pages: home, admin, analytics, compare,
│       │                   #   history, knowledge-graph, reports, settings
│       ├── components/     # UI components, assessment, digital-twin
│       ├── contexts/       # UserContext, ThemeContext
│       ├── hooks/          # useAssessment, useJobSSE
│       ├── types/          # TypeScript interfaces
│       └── utils/          # API helpers (apiFetch, apiGet, etc.)
├── backend/
│   ├── api/                # FastAPI routes (v1, v2)
│   │   └── v1/endpoints/   # auth, user_auth, intake, jobs, reports,
│   │                       #    billing, branding, portal, batch,
│   │                       #    notifications, oem, health, admin
│   ├── ai/                 # Classification, CLIP, deviation, geometry,
│   │                       #   digital twin, recommendations, generative
│   ├── core/               # Config, auth, database, models, feature flags
│   ├── infrastructure/     # FeedbackStore, FreeCADClient, Neo4j client
│   ├── optimization/       # Battery, wiring, hyperparameter tuning
│   ├── workers/            # Assessment pipeline, training scheduler
│   ├── tests/              # 400+ unit + integration tests
│   └── alembic/            # Migrations (001-008)
├── freecad-worker/         # FreeCAD CAD export container (P4)
├── infrastructure/
│   └── terraform/          # OCI provisioning (VM, network, storage)
├── docs/                   # Architecture, user guide, specs
├── scripts/                # Capture screenshots, setup Oracle VM
├── Caddyfile               # TLS reverse proxy config
├── docker-compose.yml      # Dev stack
├── docker-compose.prod.yml # Production stack
└── .env.prod.template      # Production secrets template
```

## Architecture

```
┌──────────┐     ┌──────────────┐     ┌──────────────────────┐
│ Next.js  │────▶│ FastAPI API  │────▶│ PostgreSQL 16        │
│ Frontend │     │ (v1 REST +   │     │ Redis 7 + RQ         │
│ :3000    │     │  SSE events) │     │ Neo4j (knowledge gr) │
└──────────┘     │ :8000        │     │ MailHog / SendGrid   │
                 └──────┬───────┘     └──────────────────────┘
                        │
           ┌────────────┼────────────┬───────────┐
           ▼            ▼            ▼           ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ Worker   │ │ Training │ │ FreeCAD  │ │ Stripe   │
    │ (RQ)     │ │Scheduler │ │ Worker   │ │ (billing)│
    │          │ │ (P5)     │ │ (P4)     │ └──────────┘
    └──────────┘ └──────────┘ └──────────┘
           │
           ▼
    ┌──────────────────┐
    │ SSO Providers    │
    │ Google / Azure AD│
    └──────────────────┘
```

## Testing

```bash
cd backend

# Unit tests (no database required)
pytest tests/unit/ -v

# Fast integration tests (requires PostgreSQL)
pytest tests/ -v

# Full suite including slow integration tests
pytest tests/ -v --runslow
```

**117 unit tests** (Phase 0-5, no DB) + **237 integration tests** (DB-backed).

## Configuration

Key environment variables (see `.env.prod.template`):

| Variable                | Default  | Description                    |
|-------------------------|----------|--------------------------------|
| `ENABLE_CAD_EXPORT`     | `False`  | Enable FreeCAD export          |
| `OPENAI_API_KEY`        | `""`     | OpenAI key for P3              |
| `ANTHROPIC_API_KEY`     | `""`     | Anthropic key for P3           |
| `FREECAD_HOST`          | `""`     | FreeCAD worker URL for P4      |

Two-tier auth: Workshop API key (`X-API-Key` header) + User JWT (`Authorization: Bearer`).

## Deployment

Deployed to Oracle Cloud Free Tier (ARM VM, 4 OCPU, 24 GB RAM) via GitHub Actions on push to `main`. See `scripts/setup-oracle-vm.sh` and `.github/workflows/deploy.yml`.
