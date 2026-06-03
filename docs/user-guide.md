# RetroMind AI — Workshop Operator Guide

<<<<<<< HEAD
<<<<<<< HEAD
> **RetroMind AI** — EV retrofit intelligence platform deployed on Oracle Cloud Free Tier.
=======
> **RetroMind AI v2.0** — Now with optional AI enhancements: PyTorch CNN classification, RLlib adaptive recommendations, generative design refinement, and FreeCAD CAD export. All optional capabilities are disabled by default and require configuration to activate.
>>>>>>> origin/main
=======
> **RetroMind AI v2.0** — Now with optional AI enhancements: PyTorch CNN classification, RLlib adaptive recommendations, generative design refinement, and FreeCAD CAD export. All optional capabilities are disabled by default and require configuration to activate.
>>>>>>> origin/main

This guide walks you through using RetroMind AI for your EV retrofit assessments, from first login to generating compliance reports.

---

## Table of Contents

0. [Local Development Setup](#0-local-development-setup)
1. [First-Time Setup](#1-first-time-setup)
2. [Starting an Assessment](#2-starting-an-assessment)
3. [Uploading Photos](#3-uploading-photos)
4. [The Assessment Pipeline](#4-the-assessment-pipeline)
5. [Understanding Results](#5-understanding-results)
6. [Confirming Classification](#6-confirming-classification)
7. [Viewing the Report](#7-viewing-the-report)
8. [Digital Twin](#8-digital-twin)
9. [Knowledge Graph](#9-knowledge-graph)
10. [History & Comparisons](#10-history--comparisons)
11. [Workshop Settings](#11-workshop-settings)
12. [Analytics](#12-analytics)
13. [Data Export](#13-data-export)
14. [CAD Export](#14-cad-export)
15. [CLIP Vehicle Identification](#15-clip-vehicle-identification)
16. [OEM Data Browser](#16-oem-data-browser)
17. [Troubleshooting](#17-troubleshooting)

---

## 0. Local Development Setup

Run the full stack locally on your machine.

### Prerequisites

- **Docker & Docker Compose** — for all backend services
- **Node.js 20+** — for the Next.js frontend
- **Python 3.12+** — optional, backend runs in Docker

### Step 1: Start Backend Services

```bash
# Clone the repo
git clone <repo-url> && cd RetroMindAI

# Build and start all backend containers
docker compose build
docker compose up -d
```

This starts 7 containers:
| Service | Port | Purpose |
|---------|------|---------|
| `postgres` | `5433` | Primary database |
| `redis` | `6379` | Cache + RQ job queue |
| `neo4j` | `7687`, `7474` | Knowledge graph |
| `backend-api` | `8000` | FastAPI REST API |
| `backend-worker` | — | RQ background worker |
| `training-scheduler` | — | Periodic training tasks |
| `freecad-worker` | `8100` | CAD export (STEP/STL) |

On first start the backend automatically runs Alembic migrations, seeds the demo workshop, and loads OEM data + CLIP embeddings. Wait about 30 seconds.

Get your demo API key:

```bash
docker compose logs backend-api | grep "full API key"
# Example output: Demo Workshop created with full API key: rm_4f8a3b...
```

### Step 2: Start Frontend

```bash
cd frontend
npm install

# Copy the demo key into .env.local
echo "NEXT_PUBLIC_API_KEY=rm_4f8a3b..." > .env.local

# Start Next.js dev server
npm run dev
```

### Step 3: Open the App

Go to **http://localhost:3000/auth** and click **"Use Demo Key"** to authenticate, or paste your key directly.

### Step 4: Rebuild After Changes

```bash
# Backend Python changes
docker compose build backend-api && docker compose up -d backend-api

# Both API + worker changed
docker compose build backend-api backend-worker && docker compose up -d

# FreeCAD worker
docker compose build freecad-worker && docker compose up -d freecad-worker

# Frontend — hot-reloads automatically (no rebuild needed)
```

  12. [Analytics](#12-analytics)
  13. [Data Export](#13-data-export)
  14. [Optional Capabilities](#14-optional-capabilities)
  15. [CAD Export](#15-cad-export)
  16. [Troubleshooting](#16-troubleshooting)


---

## 1. First-Time Setup

### 1.1 Accessing the Application


Open RetroMind AI in your browser:


https://your-domain.com

Open RetroMind AI in your browser. If your admin has provided a URL, use that. For local development:

### 1.2 Getting Your API Key

**Option A: Use Demo Key (for trials)**
1. The first page you see is the authentication screen.
2. Click **"Use Demo Key"** — the system automatically fetches and stores a demo API key.
3. You're redirected to the assessment workspace.

**Option B: Use Your Workshop Key**
1. Your workshop admin provides a key (e.g., `rm_4f8a3b...`).
2. Paste it into the key field and click **"Authenticate"**.

**Option C: Register a New Workshop**

curl -X POST https://api.your-domain.com/api/v1/auth/register \
=======
curl -X POST http://localhost:8000/api/v1/auth/register \

=======
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "My Workshop", "email": "owner@workshop.in"}'

Save the returned `api_key` — it won't be shown again.

### 1.3 First Look

After authentication you'll see the **New Assessment** page — a focused workspace with:
- 6 photo upload slots (3 required, 3 optional)
- A **"Start Assessment"** button (appears when all required photos are uploaded)
- Help text explaining the workflow

---

## 2. Starting an Assessment

### 2.1 The Workflow

Each assessment follows this flow:


Upload Photos → Validate → Classify Vehicle → Extract Geometry
  → Detect Deviations → Score Confidence → Assess Feasibility
  → Risk Analysis → Generate Recommendations → Build Report


You'll see progress updates as each stage completes.

### 2.2 Photo Requirements

| Slot | Required? | What to Capture |
|------|-----------|-----------------|
| Left Side Profile | **Yes** | Full left side of the vehicle, level with the chassis |
| Right Side Profile | **Yes** | Full right side, level with the chassis |
| Rear View | **Yes** | Direct rear view, centered |
| Front View | No | Direct front view, centered |
| Engine Bay | No | Engine compartment (or battery bay if empty) |
| Underbody | No | Underside, especially frame rails |

**Tips for good photos:**
- Use **diffuse daylight** (avoid harsh shadows)
- Keep the camera **level and steady**
- Include the **entire vehicle** in frame for side/rear/front views
- Avoid **obstructed** shots (people, tools, other vehicles in frame)
- Each slot allows **up to 3 attempts** if quality is poor

---

## 3. Uploading Photos

### 3.1 Upload Instructions

1. Click on an upload slot to select a file from your device.
2. The slot shows a preview thumbnail after selection.
3. Required slots show a yellow border until uploaded.
4. Uploaded slots show a green check mark if quality passes, or a warning icon if blurry.

### 3.2 Quality Checks

The system automatically checks each photo:
- **Blur detection** — Blurry photos trigger a "retake recommended" message
- **Swap detection** — If left and right side photos appear swapped, the system suggests correction
- **Occlusion** — If obstructions are detected, you're asked to recapture

### 3.3 Handling Missing Views

If a required view is missing:
- **Recovery option**: Re-upload the missing view (up to 3 attempts)
- **Continue anyway**: If you proceed without a required view, confidence is reduced and the assessment may be limited

---

## 4. The Assessment Pipeline

After clicking **"Start Assessment"**, the pipeline runs:

### 4.1 Progress Stages

| Stage | What Happens | Time |
|-------|-------------|------|
| Upload Validation | System verifies all uploaded files | ~1s |
| Image Quality | Blur, exposure, occlusion checks | ~2s |
| Vehicle Classification | CV identifies vehicle type | ~10–30s |
| Geometry Extraction | Measures proportions, bounding box | ~10–20s |
| Deviation Detection | Scans for damage, asymmetry, mods | ~15–30s |
| Feasibility Scoring | Computes confidence + feasibility | ~2s |
| Risk Analysis | Evaluates safety constraints | ~2s |
| Battery Optimization | Deviation-aware placement | ~5–15s |
| Wiring Guidance | Routing recommendations | ~3–5s |
| Digital Twin | 3D data preparation | ~3–5s |
| Finalizing | Assembles result | ~1s |

**Total target**: 60 seconds. **Hard max**: 120 seconds.

<<<<<<< HEAD
<<<<<<< HEAD
### 4.2 Progress Updates

The frontend polls the job status endpoint for live updates. If your browser supports Server-Sent Events (SSE), real-time streaming is used instead.
=======
### 4.2 SSE Progress Streaming

If your browser supports Server-Sent Events, the frontend streams progress updates in real-time. Otherwise it falls back to polling every 2 seconds.
>>>>>>> origin/main
=======
### 4.2 SSE Progress Streaming

If your browser supports Server-Sent Events, the frontend streams progress updates in real-time. Otherwise it falls back to polling every 2 seconds.
>>>>>>> origin/main

### 4.3 Timeout Handling

- At **90 seconds**: a soft warning appears — the assessment is still running
- At **120 seconds**: hard timeout — the job is marked `partial_complete` with whatever results are available
- A single **auto-retry** may be attempted if the job timed out

---

## 5. Understanding Results

### 5.1 Confidence Score

The confidence score (0–100) is your primary trust signal:

| Range | State | Meaning |
|:-----:|-------|---------|
| 85–100 | Full Confidence | All recommendations enabled; full output |
| 70–84 | Reduced Confidence | Full output with caution labels |
| 50–69 | Partial Assessment | Limited output; preliminary feasibility only |
| 0–49 | Unsafe to Assess | No recommendations; required actions listed |

**Why confidence might be reduced:**
- Missing required views (reduces Completeness score)
- Blurry or low-quality images (reduces Quality score)
- Poor structural coverage (reduces Visibility score)
- Conflicting geometry signals (reduces Geometry score)
- Uncertain deviation detection (reduces Deviation Certainty score)

### 5.2 Feasibility Label

| Label | Meaning |
|-------|---------|
| Feasible | Retrofit recommended with standard guidelines |
| Feasible with Adaptation | Retrofit possible with deviation-specific adjustments |
| Conditionally Feasible | Retrofit possible only if certain conditions are met |
| Not Currently Safe | Retrofit not recommended until evidence gaps are addressed |

### 5.3 Vehicle Classification

The system reports the detected vehicle type:
- **Three-wheeler** (auto-rickshaw)
- **Four-wheeler** (car)
- **Motorcycle**
<<<<<<< HEAD
<<<<<<< HEAD
- **Scooter**
- **Commercial**
=======
>>>>>>> origin/main
=======
>>>>>>> origin/main
- **Unknown** (insufficient evidence)

Each classification includes a confidence percentage. If confidence is below a threshold, you'll be asked to **confirm the classification** (see section 6).

### 5.4 Deviation Summary

Deviations are anomalies detected in the vehicle's structure:

| Severity | Meaning |
|----------|---------|
| Critical | Safety-critical issue (must be addressed) |
| High | Significant issue (strongly recommended to address) |
| Medium | Moderate issue (advisory) |
| Low | Minor observation (informational) |

Each deviation includes:
- **Component** — what part of the vehicle (e.g., "left frame rail")
- **Description** — plain language explanation
- **Measurements** — quantitative data where available

### 5.5 Risk Register

The risk section shows:
- **System risk state** — overall assessment of retrofit risk
- **Risk counts** — number of critical/high/medium/low risks
- **Top risks** — most important risks with descriptions

### 5.6 Recommendations

**Battery Placement:**
- Baseline recommended placement zone
- Adapted placement if deviations detected
- Explanation of why adaptation was made

**Wiring Guidance:**
- Proposed routing direction
- Highlighted caution zones
- Known risk areas for this specific vehicle

---

## 6. Confirming Classification

When the system is uncertain about the vehicle type, a confirmation dialog appears:

1. The system shows its best guess (e.g., "Vehicle classified as **three_wheeler** with 62% confidence")
2. Alternative options are listed
3. **Select the correct type** and click **Confirm**
4. The assessment re-runs feasibility scoring with your confirmation

To confirm via API:
```bash
<<<<<<< HEAD
<<<<<<< HEAD
curl -X POST https://api.your-domain.com/api/v1/jobs/{job_id}/confirm \
=======
curl -X POST http://localhost:8000/api/v1/jobs/{job_id}/confirm \
>>>>>>> origin/main
=======
curl -X POST http://localhost:8000/api/v1/jobs/{job_id}/confirm \
>>>>>>> origin/main
  -H "X-API-Key: rm_..." \
  -H "Content-Type: application/json" \
  -d '{"confirmation_type": "vehicle_classification", "selection": "three_wheeler"}'
```

---

## 7. Viewing the Report

### 7.1 Accessing the Report

After a job completes, click **"View Report"** from the assessment result page, or navigate to `/reports/{job_id}`.

### 7.2 Report Sections

The compliance report contains 13 sections:

| # | Section | Description |
|---|---------|-------------|
| 1 | Assessment Metadata | Vehicle type, confidence, feasibility, compliance state |
| 2 | Vehicle Classification | Detected type, confidence, alternatives |
| 3 | Deviation Summary | All detected anomalies with severity |
| 4 | Confidence & Risk | Confidence factors, risk state, top risks |
| 5 | Compliance State | Overall compliance determination |
| 6 | Recommendations Overview | Key recommendations summary |
| 7 | Battery Placement | Placement zones, constraints, adaptations |
| 8 | Wiring Guidance | Routing direction, caution zones |
| 9 | Cost Estimation | Estimated component and labor costs (₹ INR) |
| 10 | Tooling & Skills | Required tools and skill levels |
| 11 | Digital Twin | 3D visualization data |
| 12 | Infrastructure Degradation | System health notes |
| 13 | Retrofit DNA | Similar past jobs and patterns |

### 7.3 Exporting the Report

Click **"Export JSON"** in the report header to download the full report as a structured JSON file. Use **"Print"** for a printer-friendly version.

---

## 8. Digital Twin

The digital twin is a 3D visualization powered by Three.js:

- **Vehicle representation** — Simplified geometric model matching the classified vehicle type
- **Anomaly highlights** — Detected deviations shown as colored zones on the model
- **Placement zones** — Battery placement area shown as a transparent overlay
- **Interaction** — Rotate, pan, and zoom to inspect

---

## 9. Knowledge Graph

The knowledge graph shows the Neo4j-backed network of retrofits:

- **Nodes** — Individual retrofit jobs, vehicle types, deviation patterns
- **Edges** — Similarity relationships between jobs
- **Filters** — Filter by vehicle type, deviation severity, feasibility outcome
- **Click a node** — View the linked job's summary

Every completed job enriches the graph. Over time, similar past jobs influence recommendations for new assessments.

---

## 10. History & Comparisons

### 10.1 History Page

Access past assessments at `/history`. Shows:
- Job ID, status, vehicle type, compliance state, confidence score
- Search and filter by status
- Click any row to view the full result

### 10.2 Comparison

Navigate to `/compare` to view two assessments side-by-side. Useful for:
- Before/after comparison
- Multiple assessments of the same vehicle over time
- Comparing different vehicle types

---

## 11. Workshop Settings

Navigate to `/settings` to manage your workshop:

### 11.1 Profile Information

- **Name** — Your workshop name
- **Email** — Registration email
- **Tier** — Account tier (guest/standard)
- **API Key Prefix** — First 7 characters of your current key
- **Created** — Account creation date
- **Total Intakes / Jobs** — Usage summary

### 11.2 Renewing Your API Key

1. Click **"Renew API Key"**
2. Read the warning — this invalidates the current key
3. Click **"Yes, Renew Key"** to confirm
4. **Copy the new key immediately** — it's shown only once
5. Update any services or scripts using the old key

---

## 12. Analytics

Navigate to `/analytics` for workshop performance metrics:

### Summary Cards

- **Total Jobs** — All-time job count
- **Completed** — Successfully completed jobs
- **Avg Confidence** — Average confidence score across all jobs
- **Avg Processing** — Average time from job creation to completion

### Charts

- **Jobs per Month** — Line chart showing monthly job volume
- **Avg Confidence Score** — Confidence trends over time
- **Pass Rate** — Percentage of jobs completed or partially completed
- **Avg Processing Time** — Performance trends

### Deviation Breakdown

Shows the most common deviation types detected across all your jobs.

### Monthly Table

Detailed month-by-month breakdown with counts, averages, and status distribution.

### Time Range

Use the dropdown to switch between 6, 12, 24, or 36 months of data.

---

## 13. Data Export

Download all your workshop data from `/api/v1/workshop/export`:

```bash
curl -H "X-API-Key: rm_..." \
<<<<<<< HEAD
<<<<<<< HEAD
  https://api.your-domain.com/api/v1/workshop/export \
=======
  http://localhost:8000/api/v1/workshop/export \
>>>>>>> origin/main
=======
  http://localhost:8000/api/v1/workshop/export \
>>>>>>> origin/main
  -o my-workshop-export.json
```

The export includes:
- Workshop metadata (name, email, tier, created date)
- All intakes with view slot data and quality scores
- All jobs with status, results, and error messages

Use this for:
- Backing up your data
- Migrating to another instance
- Compliance/record-keeping

---

<<<<<<< HEAD
<<<<<<< HEAD
## 14. CAD Export

When the FreeCAD worker container is running, completed assessments can be exported as STEP or STL 3D model files. FreeCAD runs natively on ARM64 (Ubuntu apt package).

### 14.1 Starting the FreeCAD Worker

Included by default in the production stack (`docker-compose.prod.yml`). No manual action needed.

### 14.2 Exporting a Model

```bash
# STEP format (default)
curl -X GET "https://api.your-domain.com/api/v1/cad/export/{job_id}" \
=======
=======
>>>>>>> origin/main
## 14. Optional Capabilities

RetroMind AI includes several optional AI and engineering capabilities that are disabled by default. Workshop administrators can enable them by setting the appropriate environment variables and installing dependencies.

### 14.1 PyTorch CNN Classifier (Phase 1)

Replaces the heuristic vehicle classifier with a MobileNetV3-small CNN.

**Setup:**
```bash
pip install retromind[torch]
export ENABLE_PYTORCH=True
export TORCH_MODEL_PATH=/app/ai/models/vehicle_classifier.pt
```

**Behavior:** The classifier attempts PyTorch inference first. If unavailable or failed, it falls back to ONNX Runtime, then to the heuristic classifier.

### 14.2 RLlib Adaptive Recommendations (Phase 2)

Adjusts recommendation priorities and cost estimates using a PPO agent trained on historical confirmation data.

**Setup:**
```bash
pip install retromind[rllib]
export ENABLE_RL_RECOMMENDATIONS=True
```

**Admin endpoints:**
```bash
# Trigger training from historical feedback
curl -X POST http://localhost:8000/api/v1/admin/rl/train \
  -H "X-API-Key: dev-admin-key"

# Check agent status
curl http://localhost:8000/api/v1/admin/rl/status \
  -H "X-API-Key: dev-admin-key"
```

### 14.3 Generative AI Refinement (Phase 3)

Uses OpenAI GPT-4o-mini or Anthropic Claude 3.5 Haiku to refine battery zone placement and wiring routing recommendations.

**Setup:**
```bash
pip install retromind[genai]
export ENABLE_GENERATIVE_DESIGN=True
export OPENAI_API_KEY=sk-...    # or ANTHROPIC_API_KEY
```

When enabled, battery zone priorities and wiring route recommendations are passed through an LLM for expert-level review. Falls back to template values on any API failure.

### 14.4 Hyperparameter Optimization (Phase 0.5)

Uses Optuna to tune confidence weights, deviation thresholds, and stage timeouts against historical assessment data.

**Setup:**
```bash
pip install retromind[optuna]
```

**Admin endpoint:**
```bash
curl -X POST "http://localhost:8000/api/v1/admin/optimization/run?n_trials=100" \
  -H "X-API-Key: dev-admin-key"
```

Results are saved to `best_params.json` and applied automatically at runtime.

### 14.5 Continuous Learning (Phase 5)

Automatically retrains the PyTorch classifier from human-confirmed assessments on a 1-hour schedule.

**Setup:** Deployed as the `training-scheduler` Docker service (included in `docker-compose.yml`). No manual configuration needed — runs automatically when PyTorch is enabled.

## 15. CAD Export

When the FreeCAD worker container is running, completed assessments can be exported as STEP or STL 3D model files.

### 15.1 Starting the FreeCAD Worker

```bash
docker compose --profile freecad up -d
```

This starts the `freecad-worker` service on port 8100.

### 15.2 Enabling CAD Export

```bash
export ENABLE_CAD_EXPORT=True
export FREECAD_HOST=http://freecad-worker:8100
```

### 15.3 Exporting a Model

```bash
# STEP format (default)
curl -X GET "http://localhost:8000/api/v1/cad/export/{job_id}" \
<<<<<<< HEAD
>>>>>>> origin/main
=======
>>>>>>> origin/main
  -H "X-API-Key: rm_..." \
  -o assessment.step

# STL format
<<<<<<< HEAD
<<<<<<< HEAD
curl -X GET "https://api.your-domain.com/api/v1/cad/export/{job_id}?format=stl" \
=======
curl -X GET "http://localhost:8000/api/v1/cad/export/{job_id}?format=stl" \
>>>>>>> origin/main
=======
curl -X GET "http://localhost:8000/api/v1/cad/export/{job_id}?format=stl" \
>>>>>>> origin/main
  -H "X-API-Key: rm_..." \
  -o assessment.stl
```

The exported model includes:
- A simplified body representing the vehicle dimensions
- A cabin/roof overlay
- Dimensions derived from the assessment geometry data

**Note:** Returns `503 Service Unavailable` if the FreeCAD container is not running.

<<<<<<< HEAD
<<<<<<< HEAD
---

## 15. CLIP Vehicle Identification

RetroMind AI includes a zero-shot vehicle classifier powered by OpenAI CLIP (ViT-B/32). This does not require training data — it can identify any vehicle type from text prompts alone.

### How It Works

1. When you upload vehicle photos, the system may suggest known makes and models
2. CLIP compares your photos against text descriptions of each OEM model
3. Results are ranked by CLIP confidence score

### Identify-Vehicle Endpoint

```bash
curl -X POST https://api.your-domain.com/api/v1/identify-vehicle \
  -H "X-API-Key: rm_..." \
  -H "Content-Type: application/json" \
  -d '{
    "image_urls": ["https://.../photo1.jpg"],
    "make": "Bajaj",
    "model_hints": ["RE"]
  }'
```

No dataset or training is needed — CLIP works out of the box with any vehicle type.

---

## 16. OEM Data Browser

The system includes a database of OEM makes, models, generations, trims, and specifications. This data is used to inform recommendations and improve vehicle identification.

### Browsing Makes

```bash
curl https://api.your-domain.com/api/v1/oem/makes \
  -H "X-API-Key: rm_..."
```

### Browsing Models by Make

```bash
curl https://api.your-domain.com/api/v1/oem/models/Bajaj \
  -H "X-API-Key: rm_..."
```

### Viewing OEM Specs

Navigate to the OEM Admin page to view, add, or edit OEM specifications for various vehicle types.

---

## 17. Troubleshooting
=======
## 16. Troubleshooting
>>>>>>> origin/main
=======
## 16. Troubleshooting
>>>>>>> origin/main

### Common Issues

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| "401 Unauthorized" | Missing or invalid API key | Re-authenticate or renew your key |
| "429 Too Many Requests" | Daily intake limit reached | Wait until tomorrow, or contact your admin |
| Job stuck on "queued" | Worker not running | Check that the worker container is running |
| "Job not found" | Wrong job ID for this workshop | Verify the job ID and your API key |
| "400 Cannot confirm" | Job not in terminal state | Wait for job to complete; or job has no result yet |
| Low confidence all results | Poor image quality | Retake photos with better lighting and framing |
| Frontend shows blank page | API server not running | Check `docker compose ps` |
<<<<<<< HEAD
<<<<<<< HEAD
| Report says service degraded | Neo4j or Redis unavailable | Check service health indicators in report |

### Checking Service Health

The compliance report includes an **Infrastructure Degradation** section showing per-service status (green/yellow indicators) for PostgreSQL, Redis, and Neo4j.

```bash
# API health
curl https://api.your-domain.com/api/v1/health
=======
=======
>>>>>>> origin/main
| SSE not working | Proxy stripping `text/event-stream` | Frontend auto-falls back to polling |

### Checking Service Health

```bash
# API health
curl http://localhost:8000/api/v1/health
<<<<<<< HEAD
>>>>>>> origin/main
=======
>>>>>>> origin/main

# Container status
docker compose ps

# Backend logs
docker compose logs backend-api

# Worker logs
docker compose logs backend-worker

# Database
docker compose exec postgres psql -U retromind -d retromind -c "SELECT count(*) FROM jobs;"
```

### Getting Support

- Report issues at: [https://github.com/anomalyco/opencode/issues](https://github.com/anomalyco/opencode/issues)
- Include: job ID (if applicable), timestamps, and any error messages from the backend logs
