# Build Checklist

## Build Preferences

- **Build mode:** Autonomous (execution sprints + architecture review gates)
- **Comprehension checks:** N/A (autonomous mode)
- **Git:** Commit after each item using conventional commit format (`type(scope): message`). Tag architecture checkpoints (`v0.1-foundation`, etc.). `docker compose up` must always work.
- **Verification:** Checkpoint reviews every 3-4 items or at architecture boundaries (API contract, state machine, DB schema, bounded context, async lifecycle). Default to building; escalate only architectural uncertainty.
- **Check-in cadence:** N/A (autonomous mode)

## Checklist

---

- [x] **1. Foundation scaffolding — monorepo, Docker Compose, health endpoint**

  Spec ref: `spec.md > 2.3 > Monorepo Structure`

  Dependencies: None

  What: Initialize `frontend/` (Next.js + TailwindCSS + Three.js) and `backend/` (FastAPI) in monorepo. Root `docker-compose.yml` with `backend-api` (uvicorn), `postgres`, `redis`, `neo4j` (community placeholder). `.env.example` with all connection strings. FastAPI `GET /api/v1/health` returning `{"status": "ok", "services": {"postgres": "...", "redis": "...", "neo4j": "..."}}`. Frontend shell with health check display.

  Acceptance

  - Functional: `docker compose up` starts all services. Health endpoint returns all services healthy.
  - Architectural: Frontend and backend are isolated directories with no shared runtime business logic. API routes under `/api/v1/...`. No fake health values.

  Verify: Run `docker compose up`, then `curl http://localhost:8000/api/v1/health`. Confirm frontend loads at `http://localhost:3000`.

  Commit: `infra(foundation): initialize monorepo docker and health endpoint`

  Checkpoint: **YES** — architecture boundary (service topology, API prefix convention)

  Demo state: Nothing visible yet — backend health endpoint verified

---

- [x] **2. Walking skeleton E2E — fake async intake flow**

  Spec ref: `spec.md > 6 > Async Job Contract`

  Dependencies: Item 1

  What: Backend `POST /api/v1/intake` (accepts multipart images, stores reference), `POST /api/v1/intake/{id}/analyze` (returns `{"job_id": "..."}`), `GET /api/v1/jobs/{id}` (returns fake stage progression over 15s). Frontend: upload UI with view slots, polling hook with exponential backoff, assessment result card showing hardcoded feasibility score + fake vehicle class + fake risk summary. No real AI — all responses hardcoded.

  Acceptance

  - Functional: Upload images → job created → poll shows stages progressing → "complete" with fake assessment card.
  - Architectural: Frontend communicates only via REST at `/api/v1/...`. Polling via `GET /api/v1/jobs/{id}`. No fake logic in frontend — all fake data originates from backend. Async contract preserved (no WebSockets, no SSE).

  Verify: Full upload → poll → result flow in browser. Inspect network tab — confirm only REST calls to `/api/v1/...`.

  Commit: `feat(walking-skeleton): add fake async intake flow`

  Checkpoint: **YES** — architecture boundary (API contract, async transport, frontend-backend boundary)

  Demo state: End-to-end flow exists. User uploads images and sees async progress + assessment card.

---

- [x] **3. Intake + validation — guided slots, quality checks, attempt limits**

  Spec ref: `spec.md > 12.2 > Upload Workflow`

  Dependencies: Item 2

<<<<<<< HEAD
<<<<<<< HEAD
  What: Mandatory views (`left_side_profile`, `right_side_profile`, `rear_view`) enforced at intake. Optional views (`front_view`, `engine_bay`, `underbody`). Capture guidance per slot. Missing view recovery prompt + continue-with-limited-analysis path. Per-view attempt counter (max 3). Deterministic quality checks: blur detection (Laplacian variance < threshold), missing/excluded, left/right swap detection via mirror symmetry.
=======
  What: Mandatory views (`left_side_profile`, `right_side_profile`, `rear_view`) enforced at intake. Optional views (`front_view`, `engine_bay`, `underbody`). Capture guidance per slot. Missing view recovery prompt + continue-with-limited-analysis path. Per-view attempt counter (max 3). Deterministic quality checks: blur detection (Laplacian variance < threshold), missing/excluded, left/right swap detection via mirror symmetry. Skip deferred heuristics (lighting enhancement, occlusion detection, advanced geometry consistency).
>>>>>>> origin/main
=======
  What: Mandatory views (`left_side_profile`, `right_side_profile`, `rear_view`) enforced at intake. Optional views (`front_view`, `engine_bay`, `underbody`). Capture guidance per slot. Missing view recovery prompt + continue-with-limited-analysis path. Per-view attempt counter (max 3). Deterministic quality checks: blur detection (Laplacian variance < threshold), missing/excluded, left/right swap detection via mirror symmetry. Skip deferred heuristics (lighting enhancement, occlusion detection, advanced geometry consistency).
>>>>>>> origin/main

  Acceptance

  - Functional: Submit without left view → recovery prompt. Submit 3 blurry images → `unsafe_to_assess`. Swap left/right → auto-correct + confirmation prompt.
  - Architectural: View slots are typed and validated server-side. Attempt counter persisted in PostgreSQL. Deterministic checks only — no ML in intake validation.

  Verify: Upload 1/3 mandatory views → confirm recovery dialog. Upload blurry image to all 3 slots → confirm `unsafe_to_assess` on 3rd failure.

  Commit: `feat(intake): add guided upload slots and quality validation`

  Checkpoint: **NO**

  Demo state: Intake flow with real validation — graceful recovery paths visible

---

- [x] **4. Async pipeline formalization — RQ, job states, timeouts, retry**

  Spec ref: `spec.md > 4.4-4.5 > Job States, Stages`

  Dependencies: Items 2, 3

  What: Replace fake async with real RQ worker + Redis. Full job state machine (`queued → running → completed | partial_complete | failed | timed_out → retrying`). Stage enum (`upload_validation`, `image_quality_check`, `vehicle_classification`, `geometry_extraction`, `deviation_detection`, `feasibility_scoring`, `risk_analysis`, `battery_optimization`, `wiring_generation`, `digital_twin`, `finalizing`). Soft timeout warning at 90s. Hard kill at 120s with stage persistence. Auto-retry once for recoverable timeouts. Meaningful partial result threshold (minimum: classification + geometry + deviation). Job TTL (30-min resume window). Job state persisted in PostgreSQL (not Redis-only).

  Acceptance

  - Functional: Job transitions through real states. Hard timeout at 120s returns partial results if meaningful stages completed. Auto-retry on transient failure. Concurrent assessment blocked.
  - Architectural: RQ worker is separate service (`backend-worker`). Job state always persisted in PostgreSQL. Polling unchanged from walking skeleton contract. No SSE/WS.

  Verify: Start job, let it hit 120s timeout before completion → confirm `partial_complete` with meaningful partial result. Start second job while first active → confirm blocked.

  Commit: `feat(async): implement rq-based job lifecycle with timeouts`

  Checkpoint: **YES** — architecture boundary (async lifecycle, state machine, worker topology)

  Demo state: Async pipeline with real processing states. Partial results visible on timeout.

---

- [x] **5. Confidence engine + risk model — scoring, thresholds, overrides, conflict resolution**

  Spec ref: `spec.md > 9-10 > Confidence Engine, Risk, Conflict Resolution`

  Dependencies: Item 4

  What: Weighted scoring (completeness 30%, quality 20%, visibility 20%, classification 10%, geometry 10%, deviation certainty 10%). State thresholds: `full_confidence` (85-100), `reduced_confidence` (70-84), `partial_assessment` (50-69), `unsafe_to_assess` (0-49). Safety override rules (forced downgrade regardless of aggregate). Risk severity taxonomy (`low`, `medium`, `high`, `critical`). Escalation rule (>=3 high → critical blocks recommendations). System risk state separate from confidence state. Human confirmation logic for classification ambiguity (50-84 conf or moderate geometry conflict). Severe contradiction (< 40 + < 40 + weak views) → `unsafe_to_assess` without prompt. All AI inputs mocked initially — decision engine must work with synthetic test data.

  Acceptance

  - Functional: Confidence score computed from mock factors. Missing 1 mandatory view → `partial_assessment`. Moderate geometry conflict → human confirmation prompt. Severe contradiction → `unsafe_to_assess`. 3+ high risks → recommendations blocked.
  - Architectural: Confidence engine is pure domain logic (no I/O). Risk model is independent of AI outputs. Override rules are deterministic and testable.

  Verify: Submit intake with 2/3 mandatory views → confirm `partial_assessment`. Submit mock with classifier=55, geometry=moderate-conflict → confirm needs_confirmation. Submit mock with 3 high risks → confirm recommendations blocked.

  Commit: `feat(decisioning): add confidence engine risk taxonomy and conflict resolution`

  Checkpoint: **YES** — architecture boundary (decisioning layer, state machine, safety semantics)

  Demo state: Decision engine generates real confidence states and risk summaries from intake data

---

- [x] **6. AI — Vehicle classifier with ambiguity detection**

  Spec ref: `spec.md > 2.1 > AI Runtime`

  Dependencies: Items 4, 5

  What: ONNX runtime wrapper for vehicle classification model. Image preprocessing pipeline (resize, normalize, augment). Classifier output: `vehicle_type`, `confidence`, `alternatives[]` (candidates within 30% margin). Integrate with human confirmation: if confidence 50-84 → return `needs_confirmation` with options; if < 40 → check other factors for severe contradiction; if >= 85 → `human_confirmed: false`. Post-confirmation confidence boost (e.g., 58 → 75) with `human_confirmed: true` tag. Support v1 class set: `three_wheeler`, `motorcycle`, `unknown`.

  Acceptance

  - Functional: Vehicle images → classified with confidence value. Ambiguous result → confirmation modal with constrained options. Confirmed → boosted confidence + `human_confirmed` tag.
  - Architectural: ONNX model is loaded in worker only (not API). Model path configurable via env. Classification runs as async job stage. Non-blocking if model fails → FM-AI-04 fallback.

  Verify: Upload 3-wheeler photos → confirm classification with >= 85 confidence. Upload ambiguous images → confirm needs_confirmation response with options. Confirm operator selection → assessment continues with `human_confirmed: true`.

  Commit: `feat(ai): add vehicle classification with ambiguity detection`

  Checkpoint: **NO**

  Demo state: Vehicle identification shown in progress UI with confidence display

---

- [x] **7. AI — Geometry extraction**

  Spec ref: `spec.md > 2.1 > AI Runtime`

  Dependencies: Item 6

  What: Image-based structural visibility analysis. Frame approximation from multi-view images. Symmetry hint detection. Geometry consistency scoring. Output: geometry quality score (0-100), structural coverage per view, symmetry deviation estimate, `geometry_conflict` flag if inconsistencies detected. Input: classified vehicle type (provides expected geometry baseline).

  Acceptance

  - Functional: Vehicle views → geometry quality score. Asymmetric frame → geometry conflict flag. Missing view → reduced geometry coverage.
<<<<<<< HEAD
<<<<<<< HEAD
  - Architectural: Geometry stage runs after classification. Uses OpenCV for deterministic geometry hints.
=======
  - Architectural: Geometry stage runs after classification. Uses OpenCV for deterministic geometry hints. ONNX model for structural segmentation (stub if time constrained). Output feeds into confidence engine's `geometry` and visibility factors.
>>>>>>> origin/main
=======
  - Architectural: Geometry stage runs after classification. Uses OpenCV for deterministic geometry hints. ONNX model for structural segmentation (stub if time constrained). Output feeds into confidence engine's `geometry` and visibility factors.
>>>>>>> origin/main

  Verify: Upload symmetric vehicle → confirm geometry >= 70. Upload asymmetric/damaged vehicle → confirm geometry < 60 and geometry_conflict flag.

  Commit: `feat(ai): add geometry extraction from vehicle views`

  Checkpoint: **NO**

  Demo state: Structural analysis visible in assessment — geometry score and anomaly indicators

---

- [x] **8. AI — Deviation detection**

  Spec ref: `spec.md > 2.1 > AI Runtime`

  Dependencies: Item 7

  What: Deviation detection engine combining geometric and visual signals. Detectable types: asymmetry, weld modifications, structural damage, visibility gaps. Per-deviation output: type, location, severity, confidence score. Aggregation into `deviation_summary` with `anomalies_detected` count and `top_issues[]`. Feeds deviation certainty factor into confidence score. Each deviation maps to risk record (category, severity, message, recommendation, blocking flag).

  Acceptance

  - Functional: Damaged/modified vehicle → deviations detected with severity and location. Low-confidence deviation → tentative label in output. Deviations appear in risk register.
  - Architectural: Deviation output is structured list (not free-text). Each deviation maps 1:1 to a risk record. Runs as separate stage after geometry. Failures degrade to `reduced_confidence` (Tier 1).

  Verify: Upload vehicle with known weld modification → confirm detected with "high" severity in risk list. Upload clean vehicle → confirm no false-positive deviation.

  Commit: `feat(ai): add deviation detection engine`

  Checkpoint: **YES** — AI boundary complete. After this item, the system can ingest photos and produce structured intelligence.

  Demo state: Full AI pipeline — classification → geometry → deviation → risk. Deviation overlay on vehicle visualization.

---

- [x] **9. Recommendations — battery placement + wiring guidance**

  Spec ref: `spec.md > 7.5 > Recommendation API`

  Dependencies: Items 5, 8

<<<<<<< HEAD
<<<<<<< HEAD
  What: Battery placement optimization using constraint-based solver. Primary zone selection with dimension constraints (`max_width`, `max_height`, `max_depth`). Adaptation logic: when deviation detected, adjust placement (offset, shift) and document `adaptation_reason`. `risk_if_standard` field showing what would happen with non-adapted layout. `unsafe_to_recommend` when no valid placement found. Wiring guidance: primary routing path, caution zones, confidence level, confidence reason. All outputs include reasoning summaries suitable for report.
=======
  What: Battery placement optimization using constraint-based solver (SciPy/Optuna). Primary zone selection with dimension constraints (`max_width`, `max_height`, `max_depth`). Adaptation logic: when deviation detected, adjust placement (offset, shift) and document `adaptation_reason`. `risk_if_standard` field showing what would happen with non-adapted layout. `unsafe_to_recommend` when no valid placement found. Wiring guidance: primary routing path, caution zones, confidence level, confidence reason. All outputs include reasoning summaries suitable for report.
>>>>>>> origin/main
=======
  What: Battery placement optimization using constraint-based solver (SciPy/Optuna). Primary zone selection with dimension constraints (`max_width`, `max_height`, `max_depth`). Adaptation logic: when deviation detected, adjust placement (offset, shift) and document `adaptation_reason`. `risk_if_standard` field showing what would happen with non-adapted layout. `unsafe_to_recommend` when no valid placement found. Wiring guidance: primary routing path, caution zones, confidence level, confidence reason. All outputs include reasoning summaries suitable for report.
>>>>>>> origin/main

  Acceptance

  - Functional: Clean vehicle → standard layout recommended. Deviated vehicle → adapted layout with explicit reason. No safe placement → `unsafe_to_recommend` with required evidence.
  - Architectural: Recommendation engine reads from assessment output (deviation summary, risk register, confidence state). No direct DB access — consumes assessment DTO. Battery optimization runs as separate stage; failure → partial results (Tier 1).

  Verify: Upload clean vehicle → confirm `feasible` with standard layout. Upload vehicle with asymmetry → confirm `feasible_with_adaptation` with offset compensation + `adaptation_reason`. Upload vehicle with critical risk → confirm `unsafe_to_recommend`.

  Commit: `feat(recommendations): add battery placement and wiring guidance engine`

  Checkpoint: **YES** — recommendation boundary. After this, the core intelligence pipeline is complete.

  Demo state: Full retrofit recommendation with adapted battery placement, wiring path, and reasoning. Wow moment visible.

---

- [x] **10. Frontend deepening — insight cards, confirmation modal, report page**

  Spec ref: `spec.md > 12.3-12.6 > UX Decisions`

  Dependencies: Items 5, 9

  What: Progressive insight cards (one per assessment stage, renders as available). Confidence state UI with score gauge and factor breakdown. Risk register with severity badges. Confirmation modal for classification ambiguity and view swap. Assessment detail page with full decision breakdown. Compliance report page rendering all 13 sections. Polling hooks with configurable backoff. Tab close recovery state. Concurrent assessment blocking UI.

  Acceptance

  - Functional: Assessment stages render progressively as they complete. Confidence score visible with factor breakdown. Classification conflict → confirmation modal with constrained options. Report page shows all 13 sections. Return after tab close → state restored.
  - Architectural: No business logic in frontend — all data from REST. Confirmation endpoints write to backend (`POST /api/v1/jobs/{id}/confirm`). Polling stops on final state. 30-min TTL enforced server-side.

  Verify: Start assessment → confirm stages appear as they complete. Force classification ambiguity → confirm modal with radio options. Complete assessment → confirm full report with 13 sections. Close tab, reopen within 30min → confirm state restored.

  Commit: `feat(ui): add assessment workflow insight cards and report page`

  Checkpoint: **YES** — frontend/backend integration boundary. UI contract finalized.

  Demo state: Polished workshop UI with progressive insight, confirmation flow, and full report.

---

- [x] **11. Digital twin + visualization stub**

  Spec ref: `spec.md > 12.3 > UX Decisions, spec.md > 2.1 > Stack (Three.js)`

  Dependencies: Item 10

  What: Simplified 3D chassis visualization using Three.js / React Three Fiber. Basic frame geometry from classification + geometry data (stub — hardcoded 3-wheeler chassis). Highlighted deviation zones on chassis. Adapted battery placement visual overlay (showing "standard" vs "adapted" position). Fallback when unavailable (skip stage, no blocking). Runs as separate assessment stage; failure → silent degrade.

  Acceptance

  - Functional: Completed assessment → simplified 3D chassis with deviation highlights. Standard vs adapted battery overlay visible. Visualization unavailable → skipped with note; core assessment still complete.
  - Architectural: Visualization is frontend-only with data from assessment DTO. No backend 3D processing. Skip path tested.

  Verify: Complete assessment → confirm 3D chassis renders with deviation zones. Toggle "standard vs adapted" overlay. Force twin failure → confirm assessment still complete with "visualization unavailable" note.

  Commit: `feat(twin): add simplified retrofit chassis visualization`

  Checkpoint: **NO**

  Demo state: 3D chassis with deviation highlights and adapted battery placement — the visual wow moment.

---

- [x] **12. Neo4j Retrofit DNA — graph integration, similarity queries**

<<<<<<< HEAD
<<<<<<< HEAD
  Spec ref: `docs/spec.md > 3 > Bounded Contexts (intelligence_graph)`
=======
  Spec ref: `spec.md > 3 > Bounded Contexts (intelligence_graph)`
>>>>>>> origin/main
=======
  Spec ref: `spec.md > 3 > Bounded Contexts (intelligence_graph)`
>>>>>>> origin/main

  Dependencies: Item 9

  What: Neo4j schema for retrofit records (`Vehicle`, `Assessment`, `Deviation`, `Recommendation`, `Workshop` nodes + relationships). On assessment completion → persist structured graph record. Similarity query: find prior retrofits with similar deviation patterns. Heuristic fallback when Neo4j unavailable (return empty set, log degradation). Demo-grade — enough for "Retrofit DNA" narrative in demo and report section. Limit to 1-2 graph queries max.

  Acceptance

  - Functional: Completed assessment → graph record persisted. Subsequent assessment with similar deviations → "Similar prior retrofit found" note in report. Neo4j down → heuristic fallback, degradation logged.
  - Architectural: Graph writes are non-blocking (fire-and-forget or queued). Fallback is always available. No graph dependency in critical path (Tier 1 degradation).

  Verify: Complete 2 assessments with similar deviations → confirm report shows similarity match. Take Neo4j offline → confirm assessment continues with degradation note.

  Commit: `feat(graph): add retrofit dna knowledge graph with similarity queries`

  Checkpoint: **NO**

  Demo state: "Learning" narrative visible — report shows prior retrofit similarity. Degradation policy demonstrated.

---

- [x] **13. Failure mode hardening — resilience pass**

  Spec ref: `docs/failure_modes.md` (all sections)

  Dependencies: Items 4-12

  What: Wire all failure modes from `failure_modes.md` into implementation. Input failures (re-upload limits, blur/swap/occlusion detection). AI inference failures (model load error → FM-AI-04, classification conflict → prompt, severe contradiction → override). Async job failures (soft warning, hard timeout, partial results auto-retry, retry limit). Infrastructure failures (Tier 0 hard fail, Tier 1 graceful degrade with logged degradation). Safety/recommendation failures (critical blocks, high escalation, no-safe-placement). UX edge cases (rapid re-uploads tab close recovery concurrent blocking). Worker crash detection. Unsupported vehicle class handling. Infrastructure degradation telemetry in API responses.

  Acceptance

  - Functional: Forced timeout returns partial results. Neo4j unavailable → heuristic fallback. Classification conflict → human confirmation. <=2 mandatory views → `partial_assessment` or `unsafe_to_assess`. 3+ high risks → recommendations blocked. Tab close → 30-min recovery.
  - Architectural: Degradation logged in `infrastructure_degradation[]` response array. No silent failures. All non-Tier-0 failures preserve partial functionality. `docker compose up` always works.

  Verify: Run failure mode test suite — force each failure type and confirm expected fallback behavior. Verify `docker compose up` after all changes.

  Commit: `feat(resilience): wire failure modes and graceful degradation`

  Checkpoint: **YES** — resilience boundary. System hardened against all 20 failure mode types.

  Demo state: System gracefully handles timeout, infrastructure failure, and input edge cases with clear UX.

---

<<<<<<< HEAD
<<<<<<< HEAD
- [x] **14. Deployment + project state**

  Spec ref: `docs/spec.md > 2.2 > Deployment Topology`

  Dependencies: Items 1-13

  What: Production deployment on OCI Always Free Tier (Ampere A1 Flex VM) via Caddy reverse proxy + Docker Compose. Terraform provisioning for VM, VCN, block storage, object storage, DNS. CI/CD via GitHub Actions. See `docker-compose.prod.yml`, `Caddyfile`, `infrastructure/terraform/`, `.github/workflows/deploy.yml`.

  Acceptance

  - Functional: Terraform provisions infrastructure. GitHub Actions builds ARM64 images and deploys to VM on push. Caddy auto-proxies frontend + API with TLS.
  - Architectural: Single VM with Docker Compose. Caddy terminates TLS. OCI Object Storage for uploads. Neo4j AuraDB Free Tier for knowledge graph.

  Checkpoint: **YES** — release candidate.

  Demo state: Live deployment on OCI free tier with end-to-end assessment flow.
=======
=======
>>>>>>> origin/main
- [x] **14. Deployment + Devpost submission**

  Spec ref: `spec.md > 2.2 > Deployment Topology`, `prd.md > What We're Building`

  Dependencies: Items 1-13

  What: Vercel deploy for frontend (connect GitHub repo, configure build settings). Railway deploy for backend-api + backend-worker + PostgreSQL + Redis. Cloudflare R2 or S3-compatible object storage. Demo-safe seed data (2-3 known-good vehicle sets with "Try Demo Vehicle" fallback if upload pipeline fails). Screenshots: upload flow, deviation detection, adapted battery placement visual, safety report. Architecture diagrams (Mermaid from spec.md). Devpost page: project name "RetroMind AI — EV Retrofit Intelligence for Imperfect Vehicles," subheading, core story, wow moment description, tech stack tags, screenshots, repo link, deployed URL, docs artifacts (scope.md, prd.md, spec.md, checklist.md). Git tags for architecture milestones.

  Acceptance

  - Functional: Live URL loads and supports upload → async → assessment → recommendation flow with seed data. Demo-safe fallback works when upload fails. Devpost page has all required fields. Screenshots show wow moment (adapted vs standard layout).
  - Architectural: Frontend on Vercel points to Railway backend via env var. Railway services configured for independent deployability. Repo tagged with architecture milestones.

  Verify: Visit live URL → confirm end-to-end flow with seed data. Visit Devpost page → confirm green "Submitted" badge. Run `git tag` → confirm milestone tags exist.

  Commit: `infra(deploy): add vercel railway config seed data and deployment docs`

  Checkpoint: **YES** — release candidate. Production-ready demo pipeline.

  Demo state: Live deployed RetroMind with seed demo data. Devpost submission ready for judging.
<<<<<<< HEAD
>>>>>>> origin/main
=======
>>>>>>> origin/main

---

## Iteration 1

- [x] **I1. Fix confidence factor bars overflow**

<<<<<<< HEAD
<<<<<<< HEAD
  What: Backend stores confidence factors as 0-100 ints but frontend did `Math.round(value * 100)` assuming 0-1. Fixed frontend to normalize both: `Math.round((value > 1 ? value / 100 : value) * 100)`.
=======
=======
>>>>>>> origin/main
  Spec ref: `frontend/src/components/assessment/AssessmentResult.tsx:30`, `backend/workers/assessment.py:352-354`

  What: Backend stores confidence factors as 0-100 ints (`int(round(v))`) but frontend did `Math.round(value * 100)` assuming 0-1. Seed data uses 0-1, real pipeline uses 0-100. Fixed frontend to normalize both: `Math.round((value > 1 ? value / 100 : value) * 100)`.

  Acceptance: Seed demo data and live pipeline data both render correct bar widths (0-100%).

  Verify: Load seed demo and live assessment — bars fill proportionally without overflow.
<<<<<<< HEAD
>>>>>>> origin/main
=======
>>>>>>> origin/main

  Commit: `fix(ui): normalize confidence factor scale for seed and live data`

- [x] **I2. Replace hardcoded mock classifier with OpenCV heuristics**

<<<<<<< HEAD
<<<<<<< HEAD
  What: `_mock_classify()` always returned `three_wheeler` with 0.85. Replaced with `_heuristic_classify()` using OpenCV contour analysis + aspect ratio.
=======
=======
>>>>>>> origin/main
  Spec ref: `backend/ai/classification/classifier.py:75-85`

  What: `_mock_classify()` always returned `three_wheeler` with 0.85 regardless of uploaded images. Replaced with `_heuristic_classify()` that reads actual images via OpenCV, finds the largest contour, computes aspect ratio, and classifies based on vehicle proportions. Added `classifier` field ("ONNX" / "Heuristic") to vehicle classification output so frontend shows the real classifier mode.

  Acceptance: Upload wide vehicle photo → classifies as `three_wheeler`. Upload tall/narrow vehicle photo → classifies as `motorcycle`. Low-area/low-contrast images → `unknown` with low confidence.

  Verify: Upload synthetic 3-wheeler photo → confirm `three_wheeler`. Upload motorcycle photo → confirm `motorcycle`. Upload blank image → confirm `unknown`.
<<<<<<< HEAD
>>>>>>> origin/main
=======
>>>>>>> origin/main

  Commit: `feat(ai): replace hardcoded mock with opencv heuristic classification`

- [x] **I3. Fix missing upload volume on backend-api**

<<<<<<< HEAD
<<<<<<< HEAD
  What: `backend-api` had no volume mount for uploads directory. Files written by API went to ephemeral storage.
=======
=======
>>>>>>> origin/main
  Spec ref: `docker-compose.yml:38-62`

  What: `backend-api` had no volume mount for uploads directory. Files written by API went to ephemeral container storage, invisible to the worker. Added `volumes: - ./backend/uploads:/app/uploads` to `backend-api` service. Also fixed `upload_dir` config default from `/app/backend/uploads` to `/app/uploads` to match the volume mount.

  Acceptance: Uploaded files persist to host filesystem and are readable by both API and worker containers.

  Verify: Upload file via API → confirm file exists on host at `backend/uploads/{intake_id}/`.
<<<<<<< HEAD
>>>>>>> origin/main
=======
>>>>>>> origin/main

  Commit: `fix(deploy): add upload volume mount to backend-api service`

- [x] **I4. Fix numpy float32 JSON serialization in worker**

<<<<<<< HEAD
<<<<<<< HEAD
  What: OpenCV returns `numpy.float32` values not JSON serializable. Added `_make_json_safe()` recursive converter.
=======
=======
>>>>>>> origin/main
  Spec ref: `backend/workers/assessment.py`

  What: OpenCV geometry and deviation extraction returns `numpy.float32` values that are not JSON serializable. Added `_make_json_safe()` recursive converter that converts numpy types to Python natives before storing job result in PostgreSQL.

  Acceptance: All job results are JSON-serializable regardless of numpy types in AI pipeline output.

  Verify: Run full assessment pipeline → confirm job completes without `TypeError: Object of type float32 is not JSON serializable`.
<<<<<<< HEAD
>>>>>>> origin/main
=======
>>>>>>> origin/main

  Commit: `fix(worker): convert numpy types to json-safe python natives`
