# RetroMind AI — EV Retrofit Intelligence System

An end-to-end EV retrofit assessment platform for workshops. Users upload vehicle images and receive AI-powered recommendations for electric conversion, including battery placement, motor selection, wiring routing, structural analysis, and cost estimation.

## Quick Start

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
/main
```bash
git clone <repo>
docker compose up
```

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000/api/v1
- **Docs**: http://localhost:8000/docs
- **Demo API key**: printed in `backend-api` logs at startup
/main
/main
| Frontend | Next.js 14 (App Router), Tailwind CSS, TypeScript |
| API | FastAPI (Python 3.12) |
| Database | PostgreSQL 16 (SQLAlchemy ORM, Alembic migrations) |
| Cache / Queue | Redis 7 + RQ (background workers) |
| Graph | Neo4j (knowledge graph) |
| Object Storage | S3-compatible (MinIO / R2) |
/main
/main
/main
| Confidence scoring | Custom `ConfidenceEngine` with weighted factors | ✅ Active |
| Deviation detection | OpenCV circle/Hough detection + geometry analysis | ✅ Active |
| Battery zone optimization | Template-based zone matcher | ✅ Active |
| Wiring route planning | Template-based path router | ✅ Active |
| Report generation | 13-section compliance report builder | ✅ Active |
| OEM data models | SQLAlchemy + Alembic (Phase 1-2) | ✅ Active |
/main
/main

### Optional Phases (all feature-flag-gated, off by default)
| Phase | Capability | Dependencies | Flag |
|-------|-----------|-------------|------|
| P0.5 | Hyperparameter optimization (Optuna) | `optuna>=4.0` | `enable_optuna` |
| P1 | PyTorch CNN classifier (MobileNetV3) | `torch`, `torchvision` | `enable_pytorch` |
| P2 | RLlib adaptive recommendations | `ray[rllib]` | `enable_rl_recommendations` |
| P3 | Generative AI refinement | `openai>=1.0` / `anthropic` | `enable_generative_design` |
| P4 | FreeCAD CAD export (STEP/STL) | `apt: freecad` (Ubuntu ARM64) | `enable_cad_export` |
| P5 | Continuous learning pipeline | (uses P1 deps) | (auto via scheduler) |

/main
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

/main
/main
/main

## Project Structure

```
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
/main
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
/main
/main
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
/main
/main
# Unit tests (no database required)
pytest tests/unit/ -v

# Fast integration tests (requires PostgreSQL)
pytest tests/ -v

# Full suite including slow integration tests
pytest tests/ -v --runslow
```

**117 unit tests** (Phase 0-5, no DB) + **237 integration tests** (DB-backed).
/main
/main
| `ENABLE_CAD_EXPORT` | `False` | Enable FreeCAD export |
| `OPENAI_API_KEY` | `""` | OpenAI key for P3 |
| `ANTHROPIC_API_KEY` | `""` | Anthropic key for P3 |
| `FREEcAD_HOST` | `""` | FreeCAD worker URL for P4 |

## Deployment

Deployed to Oracle Cloud Free Tier (ARM VM, 4 OCPU, 24 GB RAM) via GitHub Actions on push to `main`. See `scripts/setup-oracle-vm.sh` and `.github/workflows/deploy.yml`.
/main
/main
