# RetroMind AI — Implementation Roadmap

**All 7 phases are implemented.** Below is the record of what was built.
/main
/main

---

## ✅ Phase 0 — Foundation
**Effort:** ~1 day | **Risk:** None | **Dependency for:** Everything else
/main
/main

Feature flags, capability registry, and optional dependency groups. Every new feature gates on `settings.enable_*` before loading any code.

**Files:** `backend/core/config.py`, `backend/core/capabilities.py`, `pyproject.toml`

**Status: ✅ Complete (committed)**

---

## ✅ Phase 0.5 — Hyperparameter Optimization
**Effort:** ~2 days | **Risk:** Near-zero (offline only) | **Benefit:** Improves every assessment
/main
/main

Optuna tuning for 5 targets: confidence weights, classifier signals, deviation thresholds, safety overrides, stage timeouts.

**Files:** `backend/optimization/hyperparameter/` (5 tuners, StudyRunner, ConfigOverrides, admin endpoints)

**Status: ✅ Complete (committed)**

---

## ✅ Phase 1 — PyTorch CNN Classifier
**Effort:** ~3 days | **Risk:** Low (falls back to ONNX → heuristic) | **Benefit:** Replaces RandomForest with real CNN
/main
/main

- `PyTorchRunner`, MobileNetV3-small model, fallback chain (PyTorch → ONNX → heuristic)
- `train_pytorch.py` with accuracy validation before deploy

**Files:** `backend/ai/models/pytorch_runner.py`, `backend/ai/models/cnn_model.py`, `backend/ai/train_pytorch.py`, modified `classifier.py`

**Status: ✅ Complete (committed)**

---

## ✅ Phase 2 — RL Adaptive Recommendations
**Effort:** ~5 days | **Risk:** Low (template is always the fallback) | **Benefit:** Recommendations improve with use
/main
/main

- `RLRecommendationAgent` on top of template engine
- `FeedbackStore`, `RecommendationFeedback` table (migration 005)
- `POST /admin/rl/train`, `GET /admin/rl/status`

**Files:** `backend/ai/recommendations/rl_agent.py`, `train_rl.py`, `admin_endpoints.py`, `infrastructure/feedback_store.py`, modified `engine.py`

**Status: ✅ Complete (committed)**

---

## ✅ Phase 3 — Generative Refinement
**Effort:** ~4 days | **Risk:** Low (pass-through on failure) | **Benefit:** Smart battery/wiring proposals
/main
/main

- `GenerativeRefiner` with OpenAI/Anthropic backends
- Refines battery zones and wiring routes; pass-through on any failure

**Files:** `backend/ai/generative/refiner.py`, modified `optimization/battery.py`, `optimization/wiring.py`

**Status: ✅ Complete (committed)**

---

## ✅ Phase 4 — FreeCAD CAD Export
**Effort:** ~3 days | **Risk:** Low (separate container) | **Status:** Deployable

FreeCAD worker produces STEP/STL 3D model exports from assessment data. Runs as a separate container. `freecad` is available on ARM64 via Ubuntu apt.

- `FreeCADClient`, `freecad-worker/` container
- `GET /api/v1/cad/export/{id}` returns STEP/STL
- Feature flag `enable_cad_export=true` in production
- Built from `ubuntu:24.04` base (ARM64 native via apt)

**Files:** `backend/infrastructure/freecad_client.py`, `freecad-worker/Dockerfile`, `freecad-worker/worker.py`, `backend/api/v1/endpoints/cad_export.py`

**Status: ✅ Deployable (apt package, ARM64 native)**
/main
**Effort:** ~3 days &nbsp;|&nbsp; **Risk:** Low (separate container) &nbsp;|&nbsp; **Benefit:** Downloadable STEP/STL files

- `FreeCADClient`, `freecad-worker/` container (Docker profile)
- `GET /api/v1/cad/export/{id}` returns STEP/STL

**Files:** `backend/infrastructure/freecad_client.py`, `freecad-worker/Dockerfile`, `freecad-worker/worker.py`, `backend/api/v1/endpoints/cad_export.py`

**Status: ✅ Complete (committed)**
/main
/main
/main

- `training-scheduler` container retrains every hour
- Collects human-confirmed assessments → retrains PyTorch model → validates accuracy > 75% baseline

**Files:** `backend/workers/training_scheduler.py`, migration 004, `docker-compose.yml`

**Status: ✅ Complete (committed)**

---

## ✨ Post-Phase Additions

### CLIP Zero-Shot Classification
CLIP ViT-B/32 zero-shot classifier for vehicle identification. Text embeddings cached to disk. Singleton via `get_clip_classifier()`. Used by `identify-vehicle` endpoint to rank OEM suggestions by CLIP confidence.

**Files:** `backend/ai/classification/clip_classifier.py`, `backend/ai/classification/seed_clip.py`

### OEM Data Layer (Phase 1-2)
SQLAlchemy models for makes, models, generations, trims, and OEM specs. Alembic migrations 007-008. Full REST CRUD (18 routes), 21 unit tests.

### OCI Production Config
Terraform provisioning, Caddy reverse proxy, `docker-compose.prod.yml`, `.env.prod.template`.

---

/main
## Summary

```
Phase   Description                    Files      Tests   Status
──────  ───────────                    ─────      ─────   ──────
P0      Foundation                     3           16     ✅
P0.5    Optuna hyperparameter tuning   6           12     ✅
P1      PyTorch CNN classifier         4           12     ✅
P2      RLlib recommendations          5           31     ✅
P3      Generative AI refinement       3           26     ✅
P4      FreeCAD CAD export             4           15     ✅ (ARM64 via apt)
P5      Continuous learning            3            5     ✅
───     ───────────                    ──          ───    ────
Total                                  32         132     ✅
/main
P4      FreeCAD CAD export             4           15     ✅
P5      Continuous learning            3            5     ✅
───     ───────────                    ──          ───    ────
Total                                  28         117     ✅
/main
/main
```

All optional capabilities are feature-flag-gated (default `False`) and dependency-isolated via `pyproject.toml` extras. The assessment pipeline is unchanged when all flags are off.
