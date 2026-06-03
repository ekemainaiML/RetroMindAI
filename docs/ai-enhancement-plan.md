# RetroMind AI Enhancement Plan: AI/RL/Generative/CAD Integration

## Guiding Principle
**Add, never replace.** Every new component sits *alongside* existing ones. The existing heuristic fallback chain (ONNX → OpenCV → safe default) is preserved at every layer. DegradationManager catches failures at every new component. Zero existing tests break.

---

## Architecture Safety Patterns (Already In Place)

| Pattern | File | How It Protects |
|---------|------|-----------------|
| Dual-path classifier | `ai/classification/classifier.py:22-25` | If model inference fails → heuristic fallback |
| DegradationManager | `core/degradation.py:60-67` | Tier ≥ 2 skips AI stages entirely |
| @with_retry | `core/retry.py` | Transient failures retried before degradation |
| Stage timeouts | `workers/assessment.py` (STAGE_TIMEOUTS dict) | Hung model → killed after N seconds |
| Lazy singleton loading | `workers/assessment.py:36-41` | Framework imports only when first used |
| partial_complete status | `workers/assessment.py` | Core stages done → partial result, not crash |
| Tier 3 wall | `core/degradation.py:60-67` + `workers/assessment.py` | Tier ≥ 3 forces inconclusive, score = 0 |

---

## New Safety Patterns To Add

1. **Feature flags** — env vars gating every new capability, default OFF
2. **Optional pip extras** — `pip install retromind[torch]`, `pip install retromind[rllib]`
3. **Docker Compose profiles** — `docker compose --profile gpu up`, `--profile freecad`
4. **A/B comparison store** — log both old and new recommendation quality for offline eval

---

## Phase 0: Foundation (Non-breaking, ~1 day)

### What
Add feature flags, optional dependency groups, and a capability registry.

### Changes

**`backend/core/config.py`** — add feature flags:
```python
# New settings with safe defaults
enable_pytorch: bool = False
enable_rl_recommendations: bool = False
enable_generative_design: bool = False
enable_cad_export: bool = False
torch_model_path: str = ""  # empty = use ONNX
rllib_checkpoint_path: str = ""
freecad_host: str = ""      # empty = FreeCAD unavailable
openai_api_key: str = ""    # empty = gen AI unavailable
```

**`backend/core/capabilities.py`** — new file:
```python
class CapabilityRegistry:
    """Tracks which optional systems are available at runtime."""
    _capabilities: dict[str, bool] = {}

    @classmethod
    def probe(cls, name: str, enabled: bool, check_fn: Callable) -> bool:
        available = enabled and check_fn()
        cls._capabilities[name] = available
        return available

    @classmethod
    def has(cls, name: str) -> bool:
        return cls._capabilities.get(name, False)
```

**`backend/requirements.txt`** — add optional groups:
```txt
# Core (always installed) — unchanged
fastapi==0.115.0
...

# Optional extras (pip install retromind[torch,rllib,freecad,genai])
# torch @ see pyproject.toml
# ray[rllib] @ see pyproject.toml
# freecad-python @ see pyproject.toml
# openai @ see pyproject.toml
```

**`pyproject.toml`** (new, root level):
```toml
[project.optional-dependencies]
torch = ["torch>=2.1", "torchvision>=0.16"]
rllib = ["ray[rllib]>=2.9"]
freecad = ["cadquery>=2.4"]
genai = ["openai>=1.0"]
all = ["retromind[torch,rllib,freecad,genai]"]
```

### Safety Guarantee
All flags default `False`/empty. `CapabilityRegistry.probe()` returns `False` for any uninstalled or disabled capability. No import errors, no startup failures.

---

## Phase 1: PyTorch CNN Classifier (~3 days)

### What
Replace the RandomForest training pipeline with a PyTorch CNN (MobileNetV3-small). The trained model still exports to ONNX for inference, preserving the existing `ONNXRunner` path. Add a `PyTorchRunner` for direct PyTorch inference during development.

### Architecture

```
VehicleClassifier.classify()
  ├── PyTorchRunner (if enable_pytorch=True AND capability OK)
  │   └── ONNXRunner (fallback if PyTorch fails)
  └── HeuristicClassifier (final fallback)
```

### New Files

**`backend/ai/models/pytorch_runner.py`**:
```python
class PyTorchRunner:
    """Same interface as ONNXRunner: load() → bool, run(tensor) → dict"""

    MODEL_CLASSES = ["three_wheeler", "motorcycle", "four_wheeler", "unknown"]

    def __init__(self, model_path: str = None):
        self._model = None
        self._device = None
        self._model_path = model_path or settings.torch_model_path

    def load(self) -> bool:
        if not settings.enable_pytorch:
            return False
        if not self._model_path or not os.path.isfile(self._model_path):
            logger.warning("PyTorch model not found at %s", self._model_path)
            return False
        try:
            import torch
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._model = torch.jit.load(self._model_path, map_location=self._device)
            self._model.eval()
            CapabilityRegistry.probe("pytorch", True, lambda: True)
            return True
        except ImportError:
            CapabilityRegistry.probe("pytorch", False, lambda: False)
            return False
        except Exception:
            logger.exception("Failed to load PyTorch model")
            return False

    @with_retry(retryable_exceptions=(RuntimeError,))
    def run(self, input_tensor: np.ndarray) -> dict | None:
        if self._model is None:
            return None
        try:
            import torch
            with torch.no_grad():
                tensor = torch.from_numpy(input_tensor).to(self._device)
                logits = self._model(tensor).cpu().numpy()
                probs = self._softmax(logits)
                return {
                    "logits": logits.tolist(),
                    "probabilities": probs.tolist(),
                    "predicted_class": int(np.argmax(logits)),
                }
        except Exception:
            logger.exception("PyTorch inference failed")
            return None

    def is_loaded(self) -> bool:
        return self._model is not None

    @staticmethod
    def _softmax(x):
        e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return e_x / np.sum(e_x, axis=-1, keepdims=True)
```

**`backend/ai/models/cnn_model.py`** — model definition:
```python
class MobileNetV3Classifier(nn.Module):
    """Lightweight CNN for vehicle type classification.
    4 output classes: three_wheeler, motorcycle, four_wheeler, unknown.
    ~2.5M params, runs on CPU in <50ms.
    """
    def __init__(self, num_classes=4, pretrained=True):
        super().__init__()
        from torchvision.models import mobilenet_v3_small
        self.backbone = mobilenet_v3_small(pretrained=pretrained)
        in_features = self.backbone.classifier[0].in_features
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(in_features, num_classes),
        )

    def forward(self, x):
        return self.backbone(x)
```

**`backend/ai/train.py`** — add PyTorch training path:
```python
def train_pytorch(images_dir, output_path, num_epochs=20):
    """Train MobileNetV3-small, export to TorchScript + ONNX."""
    # 1. Create dataset from labeled subdirectories
    # 2. Data augmentation: random rotation, flip, color jitter
    # 3. Train with CrossEntropyLoss + AdamW
    # 4. Export to TorchScript: torch.jit.trace()
    # 5. Export to ONNX: torch.onnx.export()
    # 6. Validate accuracy >= heuristic baseline (75%)
    #    If not, log warning and don't replace model file
```

### Modified Files

**`backend/ai/classification/classifier.py`** — add PyTorch as primary path:
```python
class VehicleClassifier:
    def __init__(self, model_path: str = None):
        self._onnx_runner = ONNXRunner(model_path)
        self._pytorch_runner = PyTorchRunner()
        self._onnx_loaded = self._onnx_runner.load()

    def classify(self, image_paths: dict[str, str]) -> dict:
        # Try PyTorch first (if enabled and loaded)
        if CapabilityRegistry.has("pytorch"):
            result = self._run_pytorch_inference(image_paths)
            if result is not None:
                return result
        # Fall back to ONNX
        if self._onnx_loaded:
            return self._run_model_inference(image_paths)
        # Final fallback: heuristic
        return self._heuristic_classify(image_paths)
```

### Safety Guarantee
- PyTorch import is lazy (inside `PyTorchRunner.load()`)
- No `torch` dependency unless `pip install retromind[torch]`
- If PyTorch fails at any point → ONNX → heuristic
- New training script never replaces a model with lower accuracy than heuristic baseline
- Docker image unchanged (no `torch` in base requirements)

---

## Phase 2: RL for Adaptive Recommendations (~5 days)

### What
Replace the template-based recommendation engine with a reinforcement learning agent (RLlib PPO). The agent learns optimal recommendation adjustments from human confirmation outcomes.

### Architecture

```
RecommendationEngine.generate()
  ├── RLAgent.generate()  (if enable_rl=True AND model loaded)
  │   └── falls back to template if RL fails/degraded
  └── TemplateEngine.generate()  (current rule-based, always available)
```

### State/Action/Reward Design

| Component | Definition |
|-----------|-----------|
| **State** | `vehicle_type` (one-hot), `confidence_score` (0-100), `deviation_severity` (0-3), `geometry_score` (0-100), `view_count` (0-6), `has_human_confirmation` (bool), `degradation_tier` (0-3) |
| **Actions** | Which recommendation categories to prioritize, cost multiplier (0.8-1.5), safety escalation level |
| **Reward** | +1 if human accepts recommendation (no override), -1 if rejected, +0.5 if confirmation was not required (implicit trust). Scaled by recommendation importance. |

### New Files

**`backend/ai/recommendations/rl_agent.py`**:
```python
class RLRecommendationAgent:
    def __init__(self, checkpoint_path: str = None):
        self._policy = None
        self._checkpoint_path = checkpoint_path or settings.rllib_checkpoint_path

    def load(self) -> bool:
        if not settings.enable_rl_recommendations:
            return False
        try:
            from ray.rllib.algorithms.ppo import PPO
            self._algorithm = PPO.from_checkpoint(self._checkpoint_path)
            CapabilityRegistry.probe("rllib", True, lambda: True)
            return True
        except ImportError:
            CapabilityRegistry.probe("rllib", False, lambda: False)
            return False
        except Exception:
            logger.exception("Failed to load RL checkpoint")
            return False

    def generate(self, assessment_result: dict) -> dict | None:
        if self._algorithm is None:
            return None
        state = self._build_state(assessment_result)
        action = self._algorithm.compute_single_action(state)
        return self._action_to_recommendations(action)

    def _build_state(self, result) -> np.ndarray:
        # Encode assessment result into fixed-size state vector

    def _action_to_recommendations(self, action) -> dict:
        # Decode action into recommendation adjustments

    def record_feedback(self, assessment_id: str, accepted: bool):
        """Log feedback for offline training."""
```

**`backend/ai/recommendations/train_rl.py`** — training script:
```python
def train_rl_from_history(db_session, num_iterations=100):
    """Train PPO agent from historical assessment + confirmation data."""
    # 1. Query all completed jobs with human_confirmation records
    # 2. Create offline dataset (state, action, reward, next_state)
    # 3. Train PPO via RLlib offline
    # 4. Evaluate: does RL agent outperform template on held-out data?
    # 5. Save checkpoint only if validation reward > template baseline
```

**`backend/infrastructure/feedback_store.py`** — feedback logging:
```python
class FeedbackStore:
    """Logs recommendation acceptance/rejection for RL training."""

    def log_feedback(self, assessment_id, recommendations, accepted, user_id):
        # INSERT INTO recommendation_feedback (...)

    def get_training_dataset(self, min_samples=100):
        # SELECT state_features, action, reward FROM feedback
        # Returns numpy arrays for RLlib offline training
```

### Modified Files

**`backend/ai/recommendations/engine.py`** — add RL path:
```python
class RecommendationEngine:
    def __init__(self):
        self._template_engine = TemplateEngine()
        self._rl_agent = RLRecommendationAgent()
        self._rl_loaded = self._rl_agent.load()

    def generate(self, assessment_result: dict) -> list[dict]:
        if self._rl_loaded:
            try:
                rl_result = self._rl_agent.generate(assessment_result)
                if rl_result:
                    return rl_result
            except Exception:
                logger.warning("RL recommendation failed, using template")
                get_degradation_manager().register("rl_engine", 1, "RL inference failed")
                self._rl_loaded = False
        return self._template_engine.generate(assessment_result)
```

**`backend/core/models.py`** — add feedback table:
```python
class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"))
    state_features = Column(JSONB)     # RL state at decision time
    action_taken = Column(JSONB)       # what was recommended
    was_accepted = Column(Boolean)     # did user accept?
    created_at = Column(DateTime(timezone=True), default=func.now())
```

### Safety Guarantee
- RL agent loads lazily; `ray[rllib]` is optional
- Template engine is *always* the fallback — RL is just an overlay
- `RLRecommendationAgent.generate()` wrapped in try/except → degradation → template
- Training script never deploys an RL model that underperforms the template baseline
- A/B comparison: both RL and template results logged; switch is configurable

---

## Phase 3: Generative AI for Adaptive Retrofit Design (~4 days)

### What
Add a generative module that proposes battery placement and wiring layout improvements using either a local model or an API (OpenAI, Claude).

### Architecture

```
BatteryOptimizer.compute_battery_zones()
  └── GenerativeRefiner.refine()  (if enabled)
      └── falls through if gen AI unavailable

WiringRouter.compute_routing()
  └── GenerativeRefiner.refine_wiring()  (if enabled)
      └── falls through if gen AI unavailable
```

### New Files

**`backend/ai/generative/__init__.py`**:
```python
from .refiner import GenerativeRefiner
```

**`backend/ai/generative/refiner.py`**:
```python
class GenerativeRefiner:
    def __init__(self):
        self._backend = None
        self._init_backend()

    def _init_backend(self):
        if not settings.enable_generative_design:
            return
        if settings.openai_api_key:
            self._backend = OpenAIBackend(settings.openai_api_key)
        elif settings.anthropic_api_key:
            self._backend = AnthropicBackend(settings.anthropic_api_key)
        # else: no generative AI

    def refine_battery_zones(self, zones: list, vehicle_type: str,
                              deviations: list, geometry: dict) -> list:
        if self._backend is None:
            return zones  # pass-through, no change
        try:
            prompt = self._build_battery_prompt(zones, vehicle_type, deviations, geometry)
            response = self._backend.complete(prompt)
            return self._parse_battery_response(response, zones)
        except Exception:
            logger.warning("Generative battery refinement failed, using template")
            get_degradation_manager().register("genai", 1, "GenAI inference failed")
            return zones  # safe pass-through

    def _build_battery_prompt(self, zones, vehicle_type, deviations, geometry):
        return f"""Given a {vehicle_type} vehicle with these characteristics:
Deviation summary: {deviations}
Geometry: {geometry}
Current recommended battery zones: {zones}

Suggest improvements to battery placement considering the actual vehicle state.
Return a JSON array of zones with priority scores."""

    def refine_wiring_routing(self, routes: list, vehicle_type: str,
                               deviations: list, battery_zone: dict) -> list:
        # Same pattern — pass-through on failure
```

### Modified Files

**`backend/optimization/battery.py`** — add gen AI refinement:
```python
from ai.generative import GenerativeRefiner

_generative_refiner = GenerativeRefiner()

def compute_battery_zones(vehicle_type: str, deviations: list,
                          geometry: dict, enable_genai: bool = True) -> list:
    zones = _template_zones(vehicle_type, deviations)
    if enable_genai and settings.enable_generative_design:
        zones = _generative_refiner.refine_battery_zones(
            zones, vehicle_type, deviations, geometry
        )
    return zones
```

### Safety Guarantee
- API keys empty by default → `_backend is None` → pass-through
- Every gen AI call wrapped in try/except → returns original zones
- No new dependencies in base requirements (API-based)
- Docker Compose unchanged
- Prompts are local strings, no data leaves memory unless API key is configured

---

## Phase 4: FreeCAD CAD Export (~3 days)

### What
Generate STEP/STL files from digital twin data using FreeCAD's Python API, running in a separate Docker container.

### Architecture

```
POST /api/v1/cad/export (new endpoint)
  │
  ├── FreeCADClient.export_step(assessment_id)
  │   │
  │   └── FreeCAD container (REST API)
  │       ├── Reads JSON spec
  │       ├── Builds 3D model
  │       └── Returns STEP/STL bytes
  │
  └── Returns 503 if FreeCAD unavailable
```

### New Files

**`backend/infrastructure/freecad_client.py`**:
```python
class FreeCADClient:
    """HTTP client to FreeCAD worker container."""

    def __init__(self):
        self._base_url = settings.freecad_host
        self._available = False

    def check_available(self) -> bool:
        if not self._base_url:
            return False
        try:
            r = httpx.get(f"{self._base_url}/health", timeout=5)
            self._available = r.status_code == 200
            return self._available
        except Exception:
            self._available = False
            return False

    def export_step(self, assessment_result: dict) -> bytes | None:
        if not self._available:
            return None
        try:
            r = httpx.post(
                f"{self._base_url}/export",
                json={"assessment": assessment_result, "format": "step"},
                timeout=120,
            )
            return r.content if r.status_code == 200 else None
        except Exception:
            logger.exception("FreeCAD export failed")
            return None
```

**`freecad-worker/Dockerfile`**:
```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y freecad-python3 && pip install fastapi uvicorn httpx
COPY worker.py /worker.py
CMD ["uvicorn", "worker:app", "--host", "0.0.0.0", "--port", "8100"]
```

**`freecad-worker/worker.py`**:
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class ExportRequest(BaseModel):
    assessment: dict
    format: str = "step"

@app.post("/export")
def export_step(req: ExportRequest):
    import FreeCAD
    import Part
    # Build 3D model from assessment data
    # Export to STEP/STL
    return Response(content=step_bytes, media_type="application/octet-stream")

@app.get("/health")
def health():
    return {"status": "ok"}
```

**`backend/api/v1/endpoints/cad_export.py`** — new endpoint:
```python
router = APIRouter()
_freecad = FreeCADClient()

@router.get("/cad/export/{assessment_id}")
def export_cad(assessment_id: str, db: Session = Depends(get_db),
               workshop: Workshop = Depends(get_workshop)):
    if not _freecad.check_available():
        raise HTTPException(503, "CAD export unavailable — FreeCAD service not running")
    job = db.query(Job).filter(Job.id == assessment_id).first()
    if not job or job.status != "completed":
        raise HTTPException(400, "Assessment not found or not completed")
    step_bytes = _freecad.export_step(job.result)
    if step_bytes is None:
        raise HTTPException(503, "CAD export failed")
    return Response(content=step_bytes, media_type="application/step",
                    headers={"Content-Disposition": f"attachment; filename={assessment_id}.step"})
```

### Docker Compose Profile

**`docker-compose.yml`** addition:
```yaml
freecad-worker:
  profiles: ["freecad"]
  build: ./freecad-worker
  ports:
    - "8100:8100"
  environment:
    - PYTHONPATH=/worker
  volumes:
    - ./freecad-worker:/worker
```

### Safety Guarantee
- FreeCAD runs isolated in its own container
- `freecad_host` defaults to `""` → `check_available()` returns `False`
- Endpoint returns 503 when FreeCAD is down (not a 500)
- No FreeCAD dependency in main backend image
- CAD export is a separate API call, not part of the assessment pipeline

---

## Phase 5: Continuous Learning Pipeline (~4 days, overlaps with Phase 1)

### What
Automate the retraining loop: collect human-confirmed assessments → periodically retrain PyTorch CNN → validate → deploy if accuracy improved.

### New Files

**`backend/workers/training.py`** — scheduled worker:
```python
def scheduled_retrain():
    """Called by cron/scheduler every N hours."""
    db = SessionLocal()
    try:
        # 1. Count unprocessed confirmed jobs
        unprocessed = db.query(Job).filter(
            Job.status == "completed",
            Job.result["vehicle_classification"]["human_confirmed"].astext == "true",
            Job.trained_on.is_(None),  # new column
        ).count()

        if unprocessed < settings.min_training_samples:
            logger.info("Only %d samples, need %d", unprocessed, settings.min_training_samples)
            return

        # 2. Collect training data
        output_dir = "/tmp/retrain_data"
        collect_training_data(db, output_dir)

        # 3. Train PyTorch model
        model_path = "/app/ai/models/vehicle_classifier_pytorch.pt"
        accuracy = train_pytorch(output_dir, model_path, num_epochs=20)

        # 4. Validate against baseline
        baseline_accuracy = get_heuristic_baseline()
        if accuracy < baseline_accuracy:
            logger.warning("New model (%.2f) < baseline (%.2f), skipping deploy", accuracy, baseline_accuracy)
            return

        # 5. Deploy: copy model + mark jobs as trained_on
        deploy_path = settings.torch_model_path or "/app/ai/models/vehicle_classifier.pt"
        shutil.copy2(model_path, deploy_path)
        db.query(Job).filter(Job.trained_on.is_(None)).update({"trained_on": func.now()})
        db.commit()
        logger.info("Deployed new model with %.2f accuracy", accuracy)

    finally:
        db.close()
```

### Modified Files

**`backend/core/models.py`** — add `trained_on` to Job:
```python
class Job(Base):
    # ... existing fields ...
    trained_on: Mapped[datetime | None] = Column(DateTime(timezone=True), nullable=True)
```

**`docker-compose.yml`** — add scheduler service:
```yaml
training-scheduler:
  build: ./backend
  command: python -c "from workers.training import scheduled_retrain; import time; [time.sleep(3600) or scheduled_retrain() for _ in iter(int, 1)]"
  depends_on: [postgres, redis]
```

### Safety Guarantee
- Training runs as a background job, not in the API request path
- Model only deploys if accuracy > heuristic baseline
- `trained_on` column tracks which jobs contributed; prevents double-counting
- Deployment is a file copy — the running inference picks it up on next `load()`
- No restart required

---

## Phase 0.5: Hyperparameter Optimization with Optuna (~2 days)

### What
Add an offline hyperparameter optimization layer using Optuna to tune the hardcoded thresholds, weights, and CV parameters that currently exist throughout the codebase. Runs as a background job, never during the assessment pipeline.

### Where Optuna Applies (7 targets found in current codebase)

| # | Target | File:Line | Current Value | What Optuna Tunes |
|---|--------|-----------|---------------|-------------------|
| 1 | Confidence Engine weights | `core/confidence.py:2-8` | `completeness=0.30, quality=0.20, ...` | 6 weights to maximize agreement with expert assessments |
| 2 | Heuristic signal weights | `ai/classification/classifier.py:86-117` | `0.30, 0.35, 0.25, 0.20, etc.` | 12+ voting weights per signal → vehicle type |
| 3 | Feature extraction params | `ai/train.py:27-28` | `Canny(50,150), blur(5,5)` | Canny low/high thresholds, blur kernel size |
| 4 | Severity thresholds | `ai/deviation/detector.py:219-224` | `<2% minor, 2-5% moderate, >5% major` | 2 threshold boundaries for 3 severity bins |
| 5 | CV detection params | `ai/deviation/detector.py:87-96` | `dp=1.2, param1=50, param2=20, ...` | 5 HoughCircles parameters |
| 6 | Safety override thresholds | `core/confidence.py:47-57` | `classification<40 AND geometry<40` | 2 classification/geometry floor values + weak_view threshold |
| 7 | Stage timeout budget | `workers/assessment.py` | `classification=20s, geometry=15s, ...` | 8 stage timeouts to minimize total pipeline time |

### Architecture

```
Offline (scheduled or manual):
  ┌─────────────────────────────────────────────┐
  │ Optuna Study: trial → sample params         │
  │   → run evaluation against historical data  │
  │   → report metric → TPE suggests next trial │
  │   → after N trials: best_params.json        │
  └─────────────────────────────────────────────┘
                          │
                          ▼
              best_params.json ← read by runtime
                          │
                          ▼
              ConfigOverrides.apply() → overrides
              hardcoded defaults with tuned values
```

### New Files

**`backend/optimization/hyperparameter/study_runner.py`**:
```python
class StudyRunner:
    """Orchestrates Optuna studies for each tuning target."""

    TARGETS = {
        "confidence_weights": tune_confidence_weights,
        "classifier_signals": tune_classifier_signals,
        "deviation_thresholds": tune_deviation_thresholds,
        "safety_overrides": tune_safety_overrides,
        "stage_timeouts": tune_stage_timeouts,
    }

    def run_all(self, db_session, n_trials=100):
        results = {}
        for name, fn in self.TARGETS.items():
            study = optuna.create_study(
                direction="maximize",
                pruner=optuna.pruners.MedianPruner(),
                study_name=name,
            )
            study.optimize(lambda trial: fn(trial, db_session), n_trials=n_trials)
            results[name] = {
                "best_params": study.best_params,
                "best_value": study.best_value,
                "trials": len(study.trials),
            }
            logger.info("Study '%s' complete: best=%.4f", name, study.best_value)
        self._save_results(results)
        return results
```

**`backend/optimization/hyperparameter/tune_confidence.py`**:
```python
def tune_confidence_weights(trial, db_session) -> float:
    """Optimize 6 confidence weights against historical human-confirmed assessments.

    Objective: maximize agreement between ConfidenceEngine score and
    human expert rating implicit in confirmation decisions.
    """
    weights = {
        "completeness": trial.suggest_float("completeness", 0.05, 0.50),
        "quality": trial.suggest_float("quality", 0.05, 0.40),
        "visibility": trial.suggest_float("visibility", 0.05, 0.40),
        "classification": trial.suggest_float("classification", 0.05, 0.30),
        "geometry": trial.suggest_float("geometry", 0.05, 0.30),
        "deviation_certainty": trial.suggest_float("deviation_certainty", 0.05, 0.30),
    }
    # Normalize to sum = 1.0
    total = sum(weights.values())
    weights = {k: v / total for k, v in weights.items()}

    # Evaluate against historical jobs
    jobs = db_session.query(Job).filter(
        Job.status == "completed",
        Job.result.isnot(None),
    ).all()

    correct = 0
    total_jobs = len(jobs)
    if total_jobs < 10:
        return 0.0  # not enough data, prune early

    from core.confidence import ConfidenceEngine
    # Temporarily override weights
    original = ConfidenceEngine.WEIGHTS.copy()
    ConfidenceEngine.WEIGHTS = weights
    try:
        for job in jobs:
            result = job.result or {}
            factors = result.get("confidence_factors", {})
            score = ConfidenceEngine.compute_score(factors)

            had_confirmation = result.get("needs_confirmation", False)
            human_confirmed = result.get("vehicle_classification", {}).get(
                "human_confirmed", False
            )

            # Reward: score > 75 AND no confirmation needed = good
            # Penalty: score > 85 but confirmation was needed = overconfident
            if score >= 75 and not had_confirmation:
                correct += 1
            elif score < 50 and had_confirmation:
                correct += 1
            elif human_confirmed and score < 50:  # human saved a bad assessment
                correct += 0.5
    finally:
        ConfidenceEngine.WEIGHTS = original

    return correct / max(total_jobs, 1)
```

**`backend/optimization/hyperparameter/tune_classifier.py`**:
```python
def tune_classifier_signals(trial, db_session) -> float:
    """Optimize heuristic classifier signal weights.

    Searches for weight combinations that maximize classification
    accuracy against a labeled ground-truth dataset.
    """
    # Each signal has per-type weights
    signal_weights = {
        "hull_shape": {
            "four_wheeler": trial.suggest_float("hull_4w", 0.1, 0.5),
            "three_wheeler": trial.suggest_float("hull_3w", 0.1, 0.5),
            "motorcycle": trial.suggest_float("hull_mc", 0.1, 0.5),
        },
        "profile_width": {
            "four_wheeler": trial.suggest_float("profile_4w", 0.1, 0.4),
            "three_wheeler": trial.suggest_float("profile_3w", 0.1, 0.4),
            "motorcycle": trial.suggest_float("profile_mc", 0.1, 0.4),
        },
        "wheel_count": {
            "four_wheeler": trial.suggest_float("wheel_4w", 0.1, 0.4),
            "three_wheeler": trial.suggest_float("wheel_3w", 0.1, 0.4),
            "motorcycle": trial.suggest_float("wheel_mc", 0.1, 0.4),
        },
    }

    # Run heuristic classifier against labeled images
    # (same logic as classifier.py but with trial weights)
    from ai.classification.classifier import VehicleClassifier, CLASS_LABELS

    labeled_dir = settings.hyperparameter_eval_dir
    if not labeled_dir or not os.path.isdir(labeled_dir):
        return 0.0

    correct = 0
    total = 0
    for label in CLASS_LABELS:
        label_dir = os.path.join(labeled_dir, label)
        if not os.path.isdir(label_dir):
            continue
        for fname in os.listdir(label_dir):
            if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            # Run heuristic with custom weights
            # (inject via a class override or test harness)
            fpath = os.path.join(label_dir, fname)
            result = _classify_with_weights(fpath, signal_weights)
            if result["vehicle_type"] == label:
                correct += 1
            total += 1

    return correct / max(total, 1) if total >= 10 else 0.0


def _classify_with_weights(image_path, weights) -> dict:
    """Replicates heuristic classify logic with tunable weights."""
    # Same OpenCV pipeline as VehicleClassifier._heuristic_classify()
    # but uses weights from trial instead of hardcoded constants
    ...
```

**`backend/optimization/hyperparameter/tune_deviation.py`**:
```python
def tune_deviation_thresholds(trial, db_session) -> float:
    """Optimize severity bin boundaries for deviation detection.

    Objective: maximize F1 score of severity classification
    (minor/moderate/major) against human-labeled deviations.
    """
    minor_cutoff = trial.suggest_float("minor_cutoff", 0.5, 4.0)      # %
    moderate_cutoff = trial.suggest_float("moderate_cutoff", 2.0, 10.0)  # %

    # ... evaluate against labeled deviation dataset ...

    return f1_score
```

**`backend/optimization/hyperparameter/tune_timeouts.py`**:
```python
def tune_stage_timeouts(trial, db_session) -> float:
    """Optimize stage timeouts to minimize total pipeline time.

    Objective: minimize average assessment time while keeping
    completion rate above 95%.
    """
    timeouts = {
        "vehicle_classification": trial.suggest_int("classif_timeout", 5, 30),
        "geometry_extraction": trial.suggest_int("geometry_timeout", 5, 25),
        "deviation_detection": trial.suggest_int("deviation_timeout", 5, 30),
        "battery_optimization": trial.suggest_int("battery_timeout", 2, 10),
        "wiring_generation": trial.suggest_int("wiring_timeout", 2, 10),
        "digital_twin": trial.suggest_int("twin_timeout", 3, 15),
    }

    # Simulate: replay historical jobs with these timeouts
    # Return: avg_completion_time if completion_rate > 0.95
    #         else 0 (prune)
    ...
```

**`backend/optimization/hyperparameter/config_overrides.py`**:
```python
class ConfigOverrides:
    """Reads best_params.json and applies tuned values at runtime."""

    OVERRIDE_PATH = Path("optimization/hyperparameter/best_params.json")

    @classmethod
    def apply(cls):
        if not cls.OVERRIDE_PATH.exists():
            return  # no overrides → use hardcoded defaults

        with open(cls.OVERRIDE_PATH) as f:
            params = json.load(f)

        # Override confidence weights
        if "confidence_weights" in params:
            from core.confidence import ConfidenceEngine
            ConfidenceEngine.WEIGHTS.update(params["confidence_weights"]["best_params"])

        # Override severity thresholds
        if "deviation_thresholds" in params:
            cls._patch_deviation_detector(params["deviation_thresholds"]["best_params"])

        # Override stage timeouts
        if "stage_timeouts" in params:
            cls._patch_stage_timeouts(params["stage_timeouts"]["best_params"])

        logger.info("Applied hyperparameter overrides from %s", cls.OVERRIDE_PATH)
```

**`backend/optimization/hyperparameter/admin_endpoints.py`** — admin-triggered optimization:
```python
router = APIRouter()

@router.post("/admin/optimization/run")
def run_optimization(
    n_trials: int = 100,
    targets: list[str] = None,
    admin: Workshop = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Run Optuna hyperparameter search (offline, may take minutes)."""
    runner = StudyRunner()
    targets = targets or list(StudyRunner.TARGETS.keys())
    # Run in background thread to avoid blocking
    thread = threading.Thread(
        target=runner.run_all,
        args=(db,),
        kwargs={"n_trials": n_trials},
    )
    thread.start()
    return {"status": "started", "targets": targets, "n_trials": n_trials}

@router.get("/admin/optimization/status")
def optimization_status(admin=Depends(get_admin_user)):
    """Check latest optimization results."""
    path = Path("optimization/hyperparameter/best_params.json")
    if not path.exists():
        return {"status": "never_run"}
    with open(path) as f:
        return {"status": "completed", "results": json.load(f)}
```

### Dependency

| Package | Type | Notes |
|---------|------|-------|
| `optuna>=4.0` | Optional | `pip install retromind[optuna]` |

### Safety Guarantee
- **Offline only**: Optuna never runs during the assessment pipeline
- **No import in hot path**: `import optuna` only inside study scripts
- **Safe defaults**: `best_params.json` absent → hardcoded values used unchanged
- **Validation gate**: Each study validates against held-out data before saving
- **Admin-gated**: Triggered via `POST /admin/optimization/run`, never automatic
- **No Docker change**: Runs on existing backend container with `pip install optuna`
- **No new infra**: Uses existing PostgreSQL to read historical jobs
- **Reversible**: Delete `best_params.json` → instantly back to hardcoded defaults
- **Isolated tests**: `pytest --skip-optional` skips Optuna-dependent tests

---

## Never-Break Checklist (Apply to Every Change)

| Rule | How It's Enforced |
|------|-------------------|
| All new deps optional | `pyproject.toml` extras, never in base `requirements.txt` |
| Lazy import | Every new framework imported inside `load()`, never at module level |
| Try/except at every IO boundary | All network calls, file reads, model loads guarded |
| Degradation on any failure | Every new component registers on failure; tier ≥ 2 skips |
| Pass-through on failure | Generative refiner returns original input; RL falls to template |
| Feature flag default OFF | `enable_*` settings all default `False` |
| Tests never require new deps | `pytest --skip-optional` skips optional-dependent tests |
| Docker Compose optional services | Use `profiles: ["freecad"]`, never in default `docker compose up` |
| Old tests must pass unchanged | `pytest tests/` with zero modification to existing tests |

---

## Dependency Matrix

| Phase | Runtime Dependency | Optional? | Docker Change |
|-------|-------------------|-----------|---------------|
| Phase 0 | None | — | None |
| Phase 0.5 | `optuna>=4.0` | `pip install retromind[optuna]` | None (runs on existing backend) |
| Phase 1 | `torch`, `torchvision` | `pip install retromind[torch]` | None (CPU torch works in current image) |
| Phase 2 | `ray[rllib]` | `pip install retromind[rllib]` | None (runs offline on worker) |
| Phase 3 | `openai` or `anthropic` | `pip install retromind[genai]` | None |
| Phase 4 | `freecad-python3` (system) | Separate container | New `freecad-worker` service (profile) |
| Phase 5 | None (uses Phase 1 deps) | — | New `training-scheduler` service |

---

## Rollout Sequence (Recommended)

```
Week 1:  Phase 0    → Feature flags + capability registry + optional deps
         Phase 0.5  → Optuna studies for 7 tuning targets, admin endpoints
                      Run studies against historical data → best_params.json
                      ConfigOverrides reads file at startup

Week 2:  Phase 1    → PyTorch CNN training + PyTorchRunner (disabled by default)
         Phase 0.5  → Re-run Optuna studies with PyTorch model as additional dimension

Week 3:  Phase 2    → RL agent shell (returns template), feedback store
                      Train RL offline from historical data
                      Flip flag: RL powers 10% of recommendations, A/B log
         Phase 0.5  → Optuna tunes RL hyperparameters (learning rate, gamma, etc.)

Week 4:  Phase 3    → Generative refiner (pass-through when disabled)
         Phase 4    → FreeCAD container + endpoint (behind profile flag)

Week 5:  Phase 5    → Automated retraining pipeline
                      Full integration test with all optional components
```

Each phase is independently deployable. Stop at any point. The core assessment pipeline never breaks.
