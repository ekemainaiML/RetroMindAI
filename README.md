# RetroMind AI — EV Retrofit Intelligence System

An end-to-end EV retrofit assessment platform for workshops. Users upload vehicle images and receive AI-powered recommendations for electric conversion, including battery placement, motor selection, wiring routing, structural analysis, and cost estimation.

## Quick Start

<<<<<<< HEAD
<<<<<<< HEAD
### Prerequisites

- Docker & Docker Compose
- Node.js 20+
- Python 3.12+ (optional — backend runs in Docker)

### 1. Start Backend Services

```bash
# Build all Docker images (first time or after backend code changes)
docker compose build

# Launch all services: PostgreSQL, Redis, Neo4j, API, Worker, FreeCAD
docker compose up -d

# Check everything is healthy
docker compose ps
```

On first startup the backend automatically runs Alembic migrations and seeds the demo workshop, OEM data, and CLIP embeddings.

Get your demo API key:

```bash
docker compose logs backend-api | grep "full API key"
# or
curl http://localhost:8000/api/v1/setup/demo-key
```

### 2. Start Frontend

```bash
cd frontend
npm install

# Set the demo API key (copy from the step above)
# Edit frontend/.env.local and set NEXT_PUBLIC_API_KEY=<your_key>

npm run dev
```

### 3. Access the App

| Service         | URL                              |
|-----------------|----------------------------------|
| Frontend        | `http://localhost:3000`          |
| API docs        | `http://localhost:8000/docs`     |
| FreeCAD worker  | `http://localhost:8100/docs`     |
| Neo4j Browser   | `http://localhost:7474`          |

Or navigate to `http://localhost:3000/auth` and click **"Use Demo Key"** to fetch the key from the running backend.

### 4. Rebuild After Code Changes

```bash
# Backend Python changes
docker compose build backend-api && docker compose up -d backend-api

# FreeCAD worker changes
docker compose build freecad-worker && docker compose up -d freecad-worker

# Frontend changes hot-reload automatically (Next.js dev server)
```
=======
=======
>>>>>>> origin/main
```bash
git clone <repo>
docker compose up
```

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000/api/v1
- **Docs**: http://localhost:8000/docs
- **Demo API key**: printed in `backend-api` logs at startup
<<<<<<< HEAD
>>>>>>> origin/main
=======
>>>>>>> origin/main

## Tech Stack

### Core
| Layer | Technology |
|-------|-----------|
<<<<<<< HEAD
<<<<<<< HEAD
| Frontend | Next.js 16 (App Router), Tailwind CSS 4, TypeScript |
| API | FastAPI (Python 3.12) |
| Database | PostgreSQL 16 (SQLAlchemy ORM, Alembic migrations) |
| Cache / Queue | Redis 7 + RQ (background workers) |
| Graph | Neo4j (retrofit DNA knowledge graph) |
| Object Storage | OCI Object Storage (S3-compatible) |
| Reverse Proxy | Caddy (auto Let's Encrypt TLS) |
=======
=======
>>>>>>> origin/main
| Frontend | Next.js 14 (App Router), Tailwind CSS, TypeScript |
| API | FastAPI (Python 3.12) |
| Database | PostgreSQL 16 (SQLAlchemy ORM, Alembic migrations) |
| Cache / Queue | Redis 7 + RQ (background workers) |
| Graph | Neo4j (knowledge graph) |
| Object Storage | S3-compatible (MinIO / R2) |
<<<<<<< HEAD
>>>>>>> origin/main
=======
>>>>>>> origin/main

### AI / ML
| Capability | Technology | Status |
|-----------|-----------|--------|
| Vehicle classification (active) | OpenCV heuristic + contour analysis | ✅ Active |
<<<<<<< HEAD
<<<<<<< HEAD
| Vehicle classification (zero-shot) | CLIP ViT-B/32 (transformers) | ✅ Active |
=======
| Vehicle classification (optional) | ONNX Runtime (scikit-learn / PyTorch exported) | ⚡ Optional |
>>>>>>> origin/main
=======
| Vehicle classification (optional) | ONNX Runtime (scikit-learn / PyTorch exported) | ⚡ Optional |
>>>>>>> origin/main
| Confidence scoring | Custom `ConfidenceEngine` with weighted factors | ✅ Active |
| Deviation detection | OpenCV circle/Hough detection + geometry analysis | ✅ Active |
| Battery zone optimization | Template-based zone matcher | ✅ Active |
| Wiring route planning | Template-based path router | ✅ Active |
<<<<<<< HEAD
<<<<<<< HEAD
| Report generation | 13-section compliance report builder | ✅ Active |
| OEM data models | SQLAlchemy + Alembic (Phase 1-2) | ✅ Active |
=======
| Report generation | Multi-section PDF-style report builder | ✅ Active |
>>>>>>> origin/main
=======
| Report generation | Multi-section PDF-style report builder | ✅ Active |
>>>>>>> origin/main

### Optional Phases (all feature-flag-gated, off by default)
| Phase | Capability | Dependencies | Flag |
|-------|-----------|-------------|------|
<<<<<<< HEAD
<<<<<<< HEAD
| P0.5 | Hyperparameter optimization (Optuna) | `optuna>=4.0` | `enable_optuna` |
| P1 | PyTorch CNN classifier (MobileNetV3) | `torch`, `torchvision` | `enable_pytorch` |
| P2 | RLlib adaptive recommendations | `ray[rllib]` | `enable_rl_recommendations` |
| P3 | Generative AI refinement | `openai>=1.0` / `anthropic` | `enable_generative_design` |
| P4 | FreeCAD CAD export (STEP/STL) | `apt: freecad` (Ubuntu ARM64) | `enable_cad_export` |
| P5 | Continuous learning pipeline | (uses P1 deps) | (auto via scheduler) |

=======
=======
>>>>>>> origin/main
| P0.5 | Hyperparameter optimization | `optuna>=4.0` | `enable_optuna` |
| P1 | PyTorch CNN classifier (MobileNetV3) | `torch`, `torchvision` | `enable_pytorch` |
| P2 | RLlib adaptive recommendations | `ray[rllib]` | `enable_rl_recommendations` |
| P3 | Generative AI refinement | `openai>=1.0` / `anthropic` | `enable_generative_design` |
| P4 | FreeCAD CAD export | `freecad-python3` (separate container) | `enable_cad_export` |
| P5 | Continuous learning pipeline | (uses P1 deps) | (auto via scheduler) |

Install optional groups:
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

<<<<<<< HEAD
>>>>>>> origin/main
=======
>>>>>>> origin/main
## API Overview

All requests require `X-API-Key` header. Admin endpoints require `ADMIN_API_KEY` (default `dev-admin-key` in dev).

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/intake` | Upload vehicle images (3-6 views) |
| `GET /api/v1/jobs/{id}` | Poll job status and results |
| `GET /api/v1/jobs/{id}/events` | SSE stream for live progress |
| `GET /api/v1/workshop/stats` | Monthly analytics |
| `GET /api/v1/workshop/profile` | Workshop profile |
| `GET /api/v1/workshop/export` | Export all assessments |
| `POST /api/v1/auth/register` | Self-service registration |
| `POST /api/v1/auth/renew` | Rotate API key |
| `GET /api/v1/reports/{id}` | Full assessment report |
<<<<<<< HEAD
<<<<<<< HEAD
| `GET /api/v1/identify-vehicle` | CLIP zero-shot vehicle identification |
=======
>>>>>>> origin/main
=======
>>>>>>> origin/main
| `GET /api/v1/admin/workshops` | List workshops (admin) |
| `GET /api/v1/admin/audit-logs` | View audit trail (admin) |
| `GET /api/v1/admin/metrics` | System metrics (admin) |
| `POST /api/v1/admin/training/start` | Train classifier (admin) |
| `POST /api/v1/admin/optimization/run` | Run Optuna studies (admin) |
| `GET /api/v1/admin/optimization/status` | Optuna results (admin) |
| `POST /api/v1/admin/rl/train` | Train RL agent (admin) |
| `GET /api/v1/admin/rl/status` | RL agent status (admin) |
<<<<<<< HEAD
<<<<<<< HEAD
| `GET /api/v1/oem/makes` | List OEM makes |
| `GET /api/v1/oem/models/{make}` | List OEM models by make |
| `GET /api/v1/cad/export/{id}` | Export STEP/STL (requires FreeCAD worker) |
=======
| `GET /api/v1/cad/export/{id}` | Export STEP/STL (requires FreeCAD) |
>>>>>>> origin/main
=======
| `GET /api/v1/cad/export/{id}` | Export STEP/STL (requires FreeCAD) |
>>>>>>> origin/main

## Project Structure

```
<<<<<<< HEAD
<<<<<<< HEAD
├── frontend/             # Next.js 16 (App Router)
│   └── src/
│       ├── app/          # Pages: assessment, reports, admin, etc.
│       └── hooks/        # useJobSSE, usePolling
├── backend/
│   ├── api/              # FastAPI routes (v1)
│   ├── ai/               # Classification, CLIP, deviation, geometry
│   ├── core/             # Config, auth, confidence, models
│   ├── optimization/     # Battery, wiring
│   ├── workers/          # Assessment pipeline, training scheduler
│   ├── tests/            # 400+ unit + integration tests
│   └── alembic/          # Migrations (001-008)
├── freecad-worker/       # FreeCAD CAD export container (P4)
├── infrastructure/
│   └── terraform/        # OCI provisioning (VM, network, storage)
├── docs/                 # Architecture, user guide, specs
├── Caddyfile             # TLS reverse proxy config
├── docker-compose.yml    # Dev stack
├── docker-compose.prod.yml  # Production stack
└── .env.prod.template    # Production secrets template
=======
=======
>>>>>>> origin/main
├── frontend/          # Next.js 14 (App Router)
│   ├── src/app/       # Pages: home, assessment, job/[id],
│   │                  #   settings, admin, analytics
│   └── src/hooks/     # useJobSSE, usePolling
├── backend/
│   ├── api/           # FastAPI routes (v1, v2)
│   ├── ai/            # Classification, deviation, geometry,
│   │                  #   digital twin, recommendations,
│   │                  #   generative (P3), PyTorch (P1)
│   ├── core/          # Config, auth, confidence, degradation,
│   │                  #   capabilities (P0), models
│   ├── infrastructure/# FeedbackStore (P2), FreeCADClient (P4)
│   ├── optimization/  # Battery, wiring, hyperparameter (P0.5)
│   ├── workers/       # Assessment pipeline, training (P5)
│   ├── tests/         # Unit tests (no DB), integration tests
│   └── alembic/       # Migrations (001-005)
├── freecad-worker/    # Standalone FreeCAD container (P4)
├── infra/             # nginx config, deploy scripts
├── docs/              # User guide, architecture, enhancement plan
├── docker-compose.yml
└── pyproject.toml     # Optional dependency groups
<<<<<<< HEAD
>>>>>>> origin/main
=======
>>>>>>> origin/main
```

## Architecture

```
┌──────────┐    ┌──────────────┐    ┌─────────────────────┐
<<<<<<< HEAD
<<<<<<< HEAD
│ Caddy    │───▶│ FastAPI API  │───▶│ PostgreSQL 16       │
│ TLS :443 │    │ (v1 REST +   │    │ Redis 7 + RQ       │
│          │    │  SSE events) │    │ Neo4j               │
└────┬─────┘    │ :8000        │    │ OCI Object Storage  │
     │          └──────┬───────┘    └─────────────────────┘
     ▼                 ▼                    ▼
┌──────────┐    ┌──────────────┐    ┌──────────────────┐
│ Frontend │    │ Worker       │    │ FreeCAD Worker   │
│ :3000    │    │ (RQ)         │    │ :8100 (STEP/STL) │
└──────────┘    └──────────────┘    └──────────────────┘
=======
=======
>>>>>>> origin/main
│ Next.js  │───▶│ FastAPI API  │───▶│ PostgreSQL 16       │
│ Frontend │    │ (v1 REST +   │    │ Redis 7 + RQ       │
│ :3000    │    │  SSE events) │    │ Neo4j               │
└──────────┘    │ :8000        │    └─────────────────────┘
                └──────┬───────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ Worker   │ │ Training │ │ FreeCAD  │
   │ (RQ)     │ │Scheduler │ │ Worker   │
   │          │ │ (P5)     │ │ (P4)     │
   └──────────┘ └──────────┘ └──────────┘
<<<<<<< HEAD
>>>>>>> origin/main
=======
>>>>>>> origin/main
```

## Testing

```bash
<<<<<<< HEAD
<<<<<<< HEAD
# All tests
pytest tests/ -v -q

# Unit tests only
pytest tests/ -v -q -m "not integration"

# Integration tests (requires PostgreSQL)
pytest tests/ -v -q -m integration
```

**401 tests** total (unit + integration).
=======
=======
>>>>>>> origin/main
# Unit tests (no database required)
pytest tests/unit/ -v

# Fast integration tests (requires PostgreSQL)
pytest tests/ -v

# Full suite including slow integration tests
pytest tests/ -v --runslow
```

**117 unit tests** (Phase 0-5, no DB) + **237 integration tests** (DB-backed).
<<<<<<< HEAD
>>>>>>> origin/main
=======
>>>>>>> origin/main

## Configuration

Key environment variables (`.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://retromind:retromind@localhost:5433/retromind` | PostgreSQL |
| `ADMIN_API_KEY` | `dev-admin-key` | Admin authentication |
| `ENABLE_PYTORCH` | `False` | Enable PyTorch CNN classifier |
| `ENABLE_RL_RECOMMENDATIONS` | `False` | Enable RLlib recommendations |
| `ENABLE_GENERATIVE_DESIGN` | `False` | Enable GenAI refinement |
<<<<<<< HEAD
<<<<<<< HEAD
| `ENABLE_CAD_EXPORT` | `False` | Enable FreeCAD export (unavailable on ARM) |
| `OPENAI_API_KEY` | `""` | OpenAI key for P3 |
| `JWT_SECRET` | auto-generated | JWT signing secret |

## Deployment

Deployed to **Oracle Cloud Always Free Tier** (Ampere A1 Flex: 4 OCPU, 24 GB RAM, 200 GB block storage). Provisioning via Terraform, deployment via GitHub Actions on push to `main`.

### Infrastructure
```
Infrastructure/terraform/   → Ampere VM, VCN, block storage,
                              DNS, object storage buckets
Caddyfile                   → Auto Let's Encrypt TLS
docker-compose.prod.yml     → Production services
.github/workflows/deploy.yml → CI/CD pipeline
```

See `infrastructure/terraform/` for provisioning and `docker-compose.prod.yml` for the production service layout.
=======
=======
>>>>>>> origin/main
| `ENABLE_CAD_EXPORT` | `False` | Enable FreeCAD export |
| `OPENAI_API_KEY` | `""` | OpenAI key for P3 |
| `ANTHROPIC_API_KEY` | `""` | Anthropic key for P3 |
| `FREEcAD_HOST` | `""` | FreeCAD worker URL for P4 |

## Deployment

Deployed to Oracle Cloud Free Tier (ARM VM, 4 OCPU, 24 GB RAM) via GitHub Actions on push to `main`. See `scripts/setup-oracle-vm.sh` and `.github/workflows/deploy.yml`.
<<<<<<< HEAD
>>>>>>> origin/main
=======
>>>>>>> origin/main
