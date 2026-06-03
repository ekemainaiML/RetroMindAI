# Process Notes

## /onboard

- Workspace check: project folder was not empty; learner chose to continue in current folder.
- Learner name shared: Ekemini Stephen.
- Who they are: identified as being in a professional role.
- Role detail: Fullstack Developer.
- Motivation signal: learner pointed to `docs/AI for EV Retrofit.docx` as what brought them to the hackathon.
- Friction: source file is binary (`.docx`) and not directly readable in-chat.
- Hackathon context shared: ET AutoTech Hackathon 2026, Theme 2 (AI for EV Retrofit & Conversion Ecosystem).
- Project framing shared: "RetroMind AI" as a self-learning EV retrofit intelligence network for imperfect real-world vehicles.
- Engagement: learner is actively providing concrete project context.
- Technical experience self-assessment: Experienced.
- Technical strengths shared in depth: Kotlin/Android/JNI/ONNX/OpenCV mobile AI pipelines; Python AI/backend orchestration; systems/controls modeling mindset.
- Desired stretch areas shared: Next.js + TypeScript, Three.js/React Three Fiber, Neo4j/knowledge graphs, practical optimization methods.
- Delivery strategy preference surfaced: 70% execution in core strengths, 30% stretch for demo differentiation.
- Engagement style: highly active, strategic, and specific; strong product + engineering framing.
- Prior AI coding agent usage: OpenCode.
- Learning goals emphasized: grow into AI systems architect (end-to-end intelligent systems), strengthen product thinking for technical systems, improve full-stack AI platform delivery, elevate engineering visualization, and sharpen leadership/prioritization under constraints.
- Resonance signal: learner prioritizes compounding career leverage over one-off demo output.
- Creative sensibility signal: strongly oriented toward technically expressive visuals (system maps, digital twins, architecture diagrams, engineering dashboards) and practical industrial AI over abstract aesthetics.
- Creative sensibility caveat: no concrete games/music preferences provided; strongest signal is technical/product taste.
- Prior SDD experience: yes (has done structured planning before building, at least informally).
- /onboard artifact created: `docs/learner-profile.md`.
- Energy/engagement read: high initiative, highly active co-creator, strategic and detailed responses.

## /scope

- Prerequisite check: `docs/learner-profile.md` exists.
- Context load: read `docs/learner-profile.md` and reviewed prior `/onboard` process notes.
- Docs scan: all files in `docs/` were checked; several upstream artifacts are binary (`.docx`, `.pptx`, `.zip`) and not directly readable in-chat.
- Mandatory Q1 (brain dump) delivered with high depth: learner defined RetroMind AI as an end-to-end autonomous EV retrofit design and validation platform.
- Core scope signal from learner: full workflow spanning vehicle scan, feasibility, battery optimization, mechanical CAD generation, wiring, and compliance checks.
- User/problem clarity signal: target users include retrofit workshops, OEM/mobility partners, and fleets in emerging markets; core pain is manual, non-standard, slow retrofit engineering.
- Active shaping: learner strongly drove direction with a complete structured proposal and explicit technical stack.
- Mandatory Q2 (research & reaction): learner resonated with all three references - generative design framing (Autodesk-style constraints), FreeCAD automation for CAD outputs, and Neo4j-style knowledge graph intelligence.
- Resonance pattern: prefers integrated differentiation story over single-feature novelty.
- Pushback received: learner rejected MVP framing and asked for full production-grade direction across all vehicle categories/features.
- Active shaping moment: learner explicitly steered scope philosophy toward maximal ambition.
- Clarification response to production bar question: learner supplied a comprehensive end-to-end product vision emphasizing self-learning retrofit intelligence graph, deviation-aware engineering, federated learning, digital twin simulation, and multi-vehicle scalability.
- Scope tension remains: ambition is ecosystem-scale; need sharper launch acceptance criteria and time-boxed boundaries for hackathon execution quality.
- Mandatory Q3/Q4 refinement outcome: learner selected a concrete launch wedge and explicit cut decisions.
- Launch wedge selected by learner: independent EV retrofit workshops (primary customer), India Tier 1/Tier 2 retrofit ecosystems (initial market), and auto-rickshaw ICE->EV conversions (initial vehicle anchor).
- Explicit out-of-scope cuts for first launch: passenger cars as initial anchor, OEM-first go-to-market, and fleet-first rollout.
- Differentiation anchor reinforced: deviation-aware battery placement AI plus Retrofit DNA knowledge graph as proof of self-learning intelligence.
- Idea evolution: moved from broad multi-vehicle production vision to a phased wedge strategy while preserving long-term platform ambition.
- Deepening round 1 started: learner introduced a detailed "master plan" covering full prototype strategy, architecture, models, UI/UX, delivery phases, demo flow, risks, and positioning; asked that execution follow it fully.
- Engagement style: strong ownership and directive steering; highly active shaping of planning direction.
- Deepening round decision: learner declined further questioning and requested progression to `/prd`; stated all plan pillars are non-negotiable.
- Deepening rounds summary: 1 round; materially improved scope by crystallizing launch wedge (workshops in India, 3-wheeler anchor) while preserving full-production platform vision.
- Pushback handling: assistant shifted from generic MVP framing to production-grade framing with explicit phased cuts.
- /scope artifact created: `docs/scope.md`.

## /prd

- Prerequisite check: `docs/scope.md` exists.
- Context load: read `docs/scope.md`, `docs/learner-profile.md`, and prior `/scope` process notes.
- Docs scan: all files in `docs/` were checked; `.docx`, `.pptx`, and `.zip` artifacts remain binary and not directly readable in-chat.
- Mandatory Q1 (walkthrough start) produced high-specificity first-run behavior: guided engineering workspace first (not dashboard), single dominant CTA to upload/scan vehicle, and rapid visible AI analysis feedback.
- Core UX decision from learner: "show intelligence before navigation" with first wow moment anchored on deviation-aware adaptation after upload.
- Acceptance-direction signal: first-time flow should establish trust/confidence in first 30 seconds through structured analysis outputs and clear feasibility summary.
- Mandatory Q2 (core user stories) refinement: learner approved story direction but tightened wording to explicitly include structural condition analysis, deviation detection, trustworthy feasibility, and adaptive recommendations.
- Learner-proposed epic decomposition: Guided Retrofit Assessment with onboarding, vehicle intelligence, feasibility intelligence, and adaptive intelligence stories.
- Learner added concrete acceptance-criteria structure (Given/When/Then), including guided image-slot requirements and completeness validation prior to analysis.
- Active shaping signal: learner is driving high-rigor requirement quality and pushing for differentiation language in every story.
- Mandatory Q3 (acceptance specificity) captured explicit timing requirements: first feasibility result target 30-60 seconds, hard max 2 minutes; progressive disclosure strategy preferred over monolithic wait.
- SLA framing chosen by learner: optimize for "time to first trustworthy insight" with staged outputs (identification, structural scan, feasibility, adaptive recommendation, twin view).
- Mandatory Q4 (edge cases) produced detailed graceful-degradation policy: continue with reduced confidence by default, block only for safety-critical missing visibility.
- Edge-case behaviors defined by learner: missing/blurred/inconsistent images, swapped left-right detection with confirmation, low-light auto-enhancement, optional underbody handling, occlusion warnings, contradictory vehicle-class resolution.
- Trust model emphasized: explicit confidence reporting and reason codes required on assessments.
- Requirement quality signal: learner converted abstract edge-case prompt into executable state model and testable criteria.
- Scope guard response: learner explicitly kept all discussed features in-scope for hackathon build and did not defer features.
- Pushback: learner rejected feature deferral framing; strong preference for full inclusion.
- What changed vs scope: scope-level vision was expanded into explicit epics/stories, testable acceptance criteria, timing SLAs, confidence-state behavior, and recovery logic for messy workshop inputs.
- Notable "what if" depth: learner surfaced robust handling for missing/blurred/inconsistent uploads, swapped views, low light, occlusion, uncertain classification, and safety-critical hard-stop conditions.
- Strong stance moments: learner repeatedly insisted on full feature inclusion and immediate progression to artifact generation.
- Scope guard outcome: no functional deferrals accepted; breadth retained with expectation of execution via progressive insight flow.
- Deepening rounds: 0 during `/prd` (learner chose direct artifact generation after mandatory coverage); context still materially strengthened by highly detailed mandatory responses.
- Active shaping: learner drove requirement wording, story decomposition, acceptance structure, and SLA definitions; assistant role was primarily clarification and formalization.
- /prd artifact created: `docs/prd.md`.

## /spec

- Prerequisite check: `docs/scope.md` and `docs/prd.md` exist.
- Context load: read `docs/learner-profile.md`, `docs/scope.md`, `docs/prd.md`, and prior process notes.
- Docs scan: all files in `docs/` were checked; `.docx`, `.pptx`, and `.zip` artifacts remain binary and not directly readable in-chat.
- Reference review completed: read `skills/hackathon-guide/references/spec-patterns.md` and prepared to map PRD epics to concrete architecture components.
- Mandatory Q1 (tech preferences): learner confirmed locking architecture to the proposed preferred stack (Next.js/Tailwind + FastAPI + AI/graph/CAD toolchain).
- Mandatory Q2 (deployment): learner wants both local development workflow and deployed production URL.
- Mandatory Q3 (stack research): reviewed current docs/maintenance signals for Next.js, Tailwind, FastAPI, ONNX Runtime, PyTorch, OpenCV, PostgreSQL, MongoDB, FreeCAD, plus deployment pricing constraints (Vercel/Railway) and Neo4j Aura pricing tiers.
- Learner accepted deployment split with modifications: keep Vercel + Railway + Railway Postgres + Neo4j Aura, add object storage (Cloudflare R2 or S3-compatible), and defer MongoDB for v1.
- Architecture direction reinforced by learner: start as one deployable FastAPI service with internal modules (api/ai/workers/optimization/graph) to avoid premature microservice overhead.
- Execution strategy decision: async job pattern required (`POST` returns `job_id`, frontend polls `GET /jobs/{id}`) instead of blocking analysis requests.
- Infra parity preference: local Docker Compose stack with Next.js, FastAPI, Postgres, Neo4j, Redis, optional MinIO; cloud path via Vercel + Railway + Aura + R2.
- Active shaping: learner provided concrete production-friendly constraints, cost posture, and sequencing rationale; strong technical ownership.
- Architecture mapping direction: epic-by-epic PRD-to-component traceability style is being used as the primary spec structure to keep `/checklist` and `/build` references stable.
- Diagramming standard decision: Mermaid locked as canonical diagram format across spec docs; ASCII reserved for file trees and tiny inline flow notes.
- Learner supplied explicit diagram taxonomy for spec quality: epic workflows, PRD-to-component mapping, async sequence diagrams, service boundaries, deployment topology, and optional domain graph modeling.
- Core architecture decision finalized for confidence engine: weighted Assessment Confidence Score (0-100) with explicit weights (completeness 30, quality 20, visibility 20, classification 10, geometry 10, deviation certainty 10).
- State thresholds locked by learner: full_confidence 85-100, reduced_confidence 70-84, partial_assessment 50-69, unsafe_to_assess 0-49.
- Safety policy locked: hard safety overrides can force downgrade regardless of aggregate score; learner provided explicit override triggers for partial and unsafe states.
- Requirement clarity gain: confidence states now have strict UX behavior contracts and recommendation-gating rules, strengthening /build verifiability.
- Async transport decision locked by learner: polling-only in v1 (`GET /jobs/{id}`), SSE as v1.5 enhancement, WebSockets explicitly out of v1 scope.
- Contract details added by learner: job status/state enums, stage enums, recommended polling cadence/backoff, and transport abstraction pattern for future SSE migration.
- Architecture discipline signal: learner is sequencing complexity intentionally (ship reliability first, stream upgrades later).
- Queue stack decision locked: `RQ + Redis` for v1 background execution; Celery and Dramatiq explicitly deferred.
- Learner rationale: prioritize low complexity, reliability, and ship speed; avoid distributed orchestration overhead in v1.
- Data durability decision: job progress/state should persist in PostgreSQL (not Redis-only) for observability and recovery.
- Cloud topology refinement: single codebase with separate Railway services (`backend-api`, `backend-worker`, `redis`, `postgres`).
- Access-control decision locked: single-tenant demo mode (no auth) for v1, with explicit auth-ready architecture boundaries from day one.
- Tenant strategy set: use implicit `demo-workshop` context and workshop-scoped entities/services now, enabling low-friction migration to real multi-tenant auth later.
- Scope discipline: learner explicitly deprioritized identity features in favor of core engineering-intelligence differentiation.
- Safety-input contract locked for v1: mandatory views are `left_side_profile`, `right_side_profile`, and `rear_view`; `front_view`, `engine_bay`, and `underbody` are optional.
- Deterministic gating rule locked: 3/3 mandatory valid => eligible to score; 2/3 => `partial_assessment`; <2 => `unsafe_to_assess`.
- Additional safety overrides reinforced: low mandatory-view quality and severe geometry/classification uncertainty can force downgrade regardless of base scoring.
- Risk severity taxonomy locked: `low` / `medium` / `high` / `critical` (engineering severity model, not UI-style warn/info model).
- Blocking policy locked: only `critical` blocks recommendations directly; `high` requires mitigation but is non-blocking unless escalated.
- Escalation rule locked: 3 or more `high` risks escalate to critical system risk state and block recommendations.
- Risk-model structure expanded by learner: each risk should include category, severity, message, recommendation, blocking flag, and confidence; separate `system_risk_state` from confidence state.
- Compliance output contract locked: single canonical v1 "Retrofit Safety & Feasibility Report" with 13 mandatory sections and explicit required fields per section.
- Positioning decision: v1 report is advisory/compliance-oriented (safety readiness), not a formal certification artifact.
- Enum and decision-contract additions from learner: recommendation status set (`feasible`, `feasible_with_adaptation`, `limited_feasibility`, `unsafe_to_recommend`) plus compliance-state vocabulary.
- Explainability requirement reinforced: recommendations must include reasoning and confidence/limitation context suitable for workshop users, judges, and investors.
- File-structure and boundary decision: learner confirmed monorepo for v1 but requires strict API boundary (no shared runtime business logic between frontend/backend) and independent deployability.
- API surface decision locked: REST-only in v1 with versioned routes under `/api/v1/...`; GraphQL explicitly deferred.
- API design preference: workflow-oriented REST resources (intake/jobs/assessments/compliance/reports/retrofits) with FastAPI OpenAPI docs used as a delivery asset.
- Backend bounded-context refinement provided by learner: canonical v1 contexts should be `intake`, `jobs`, `assessments`, `recommendations`, `reports`, `intelligence_graph`, `shared`.
- Domain-boundary rule clarified: `risks` and `compliance` remain subdomains under `assessments` in v1 (not standalone top-level contexts).
- Structural nuance: `retrofits` context should be optional/deferred unless explicit retrofit lifecycle persistence is required in v1.
- Architecture quality signal: learner is optimizing for capability-based boundaries and avoiding premature fragmentation.
- Final boundary lock: exclude top-level `retrofits` context in v1; model retrofit as composed workflow `intake -> assessment -> recommendation -> report`.
- Product-scope rationale: v1 focuses on engineering intelligence decision pipeline, not workshop operations lifecycle management.
- Evolution plan acknowledged: defer explicit retrofit lifecycle bounded context to later phase when operational states/workflows are truly supported.
- Deepening round 1 initiated for `/spec`: learner requested structured pressure-testing of failure modes, graceful degradation, and safety refusal logic prior to final spec generation.
- Proposed failure analysis axes from learner: input failures, AI inference failures, async job failures, recommendation safety failures, infrastructure failures, UX failures, and abuse/edge cases.
- Input failure lock: maximum 3 guided re-upload attempts per mandatory view before forcing `unsafe_to_assess` and stopping recommendation generation.
- AI conflict-resolution policy locked (deepened): full deterministic priority rule set — 1) human confirmation, 2) auto-correction if obvious, 3) partial downgrade, 4) unsafe refusal.
- Three case types defined:
  - Case 1 (recoverable ambiguity): classification_conf 50-84 or geometry_conflict moderate → human confirmation prompt; eligible for `reduced_confidence` or `full_confidence` after confirmation; manual input restores confidence; `human_confirmed` trace tag applied.
  - Case 2 (unresolved conflict): operator skips or conflict persists → `partial_assessment` with reason `unresolved_model_conflict`; preliminary feasibility guidance allowed, strong recommendations blocked.
  - Case 3 (severe contradiction): classifier_conf < 40 AND geometry_consistency < 40 AND mandatory views weak → `unsafe_to_assess`; human prompt not sufficient; safety override.
- UX pattern locked: confirmation modal / inline decision card with constrained selection (radio buttons, never free-text). Example: "Auto Rickshaw (58%) / Motorcycle (31%) / Re-upload Photos". No "What vehicle is this?" style prompts.
- Confidence effect of human confirmation: raw classifier confidence (e.g. 58) → effective_confidence (e.g. 75) after operator confirms; tagged `human_confirmed: true` for explainability. Report line: "Vehicle classification was manually confirmed due to model ambiguity."
- API contract locked: `status: "needs_confirmation"`, `reason: "vehicle_classification_conflict"`, `options[]` with `vehicle_type` and `confidence` per candidate.
- Acceptance criteria locked: Given AI model disagreement, when recoverable → surface prompt, present constrained options, continue after confirmation, record manual override. If unresolved → downgrade to `partial_assessment`, reduce confidence, limit recommendations. Critical thresholds → `unsafe_to_assess`.
- Async job timeout policy locked: partial results if available (primary), graceful kill + one auto-retry (secondary), never blind kill + user retry only. Hard timeout at 120s with stage-aware recovery. Soft warning at 90s.
- Timeout recovery: persist completed stages, terminate worker, auto-retry once if recoverable, return partial_assessment or unsafe_to_assess based on "meaningful partial result" threshold (minimum: vehicle_classification + geometry_extraction + deviation_detection; preferably + feasibility_scoring).
- New job states added: `retrying`, `timed_out`, `partial_complete`. Full enum: `queued`, `running`, `retrying`, `completed`, `partial_complete`, `failed`, `timed_out`, `cancelled`.
- Infrastructure degradation policy locked: per-service tiered degradation with Tier 0-3 model.
  - Tier 0 (hard fail): FastAPI API, PostgreSQL, Redis/RQ, core inference runtime → `unsafe_to_assess`.
  - Tier 1 (graceful degrade): Neo4j Aura → heuristic fallback; Cloudflare R2 → temp local storage; battery optimizer → partial results; wiring engine → partial results; digital twin → skip stage.
  - Tier 2 (silent graceful degrade): report export, SSE fallback to polling, analytics → no workflow interruption.
  - Tier 3 (ignore): UI visual polish, non-core visuals.
  - Infrastructure_degradation array added to API response contracts with service, severity, fallback per entry.
- UX edge case policy locked: best-effort resilient model.
  - Rapid re-uploads: latest valid upload wins; UI debounce only (1-2s); re-analysis auto-triggered on changed mandatory image; cancels stale downstream stages safely.
  - Tab close/refresh: job continues server-side; recoverable for 30 min TTL.
  - Concurrent assessments: blocked in v1 (1 active job per workshop); same-intake edits allowed to restart analysis.
- /spec deepening round COMPLETE — all 7 failure-mode categories locked: input, AI inference, async job, recommendation safety, infrastructure, UX, abuse/edge cases.

## /checklist

- Prerequisites verified: `docs/spec.md` and `docs/prd.md` exist. Full context loaded from all docs/ files and conversation history.
- Sequencing logic: learner rejected backend-heavy ordering in favor of walking skeleton first. Strong rationale: validate API contracts, async UX, frontend/backbone boundaries before deep intelligence.
- Key sequencing change: confidence engine + risk model moved before AI engines (decisioning layer should work with mocks first). Frontend deepening moved after recommendations (avoids building UI twice). Neo4j moved near end (differentiator, not critical path). Failure modes layered continuously (not bolted on at end).
- Final order: 14 items — Foundation → Walking Skeleton → Intake → Async Pipeline → Confidence/Risk → AI (classifier, geometry, deviation) → Recommendations → Frontend → Digital Twin → Neo4j → Failure Hardening → Devpost.
- Build mode: Autonomous with structured checkpoints. Pause every 3-4 items or at architecture boundaries (API contract, state machine, DB schema, bounded context, async lifecycle). Checkpoints at items 1, 4, 5, 8, 9, 10, 13, 14.
- Git cadence: commit after each checklist item using conventional commits (`type(scope): message`). Tag architecture checkpoints (`v0.1-foundation`, etc.). `docker compose up` must always work.
- Verification: checkpoint reviews at architecture boundaries. Default to building; escalate only architectural uncertainty.
- Format refinements from learner: added Dependencies field, Commit field, Functional vs Architectural acceptance split, Checkpoint flag, Demo state per item.
- API correction: `POST /intake/analyze` (not `POST /jobs`) returns job_id — jobs are internal consequences, not user-initiated resources.
- Item count: 14 (expanded from 12 — split frontend+twin into two, added failure mode hardening as standalone item).
- Estimated build time: 3-5 hours depending on AI model integration complexity.
- Devpost planning: core story locked — "RetroMind AI helps retrofit workshops safely convert imperfect vehicles into EVs by adapting engineering decisions to structural deviations automatically." Wow moment: "Standard retrofit unsafe → RetroMind adapts layout automatically." Deploy: YES (Vercel + Railway, thin demo-safe slice with seed data).
- Learner engagement: highly active, strong opinions on sequencing and execution methodology. Drove format refinements and architectural ordering independently.
- Deepening rounds: 0 (learner chose to proceed directly after mandatory questions — response was detailed enough that deepening was unnecessary).

## /build

- Build mode: Autonomous with structured checkpoints.
- All 14 checklist items completed across 7 dispatched subagent tasks.
- Architecture checkpoints: `v0.1-foundation`, `v0.2-async-pipeline`, `v0.3-decision-engine`, `v0.4-deviation-engine`, `v0.5-digital-twin`, `v0.6-resilience`, `v0.7-release-candidate`.
<<<<<<< HEAD
<<<<<<< HEAD
- 401 tests passing (no regressions).
=======
- 138 tests passing (no regressions).
>>>>>>> origin/main
=======
- 138 tests passing (no regressions).
>>>>>>> origin/main
- Docker Compose boot verified — full stack (postgres, redis, neo4j, backend-api, backend-worker) all healthy.
- Frontend production build succeeds.
- Seed demo data created — `POST /api/v1/demo/0` returns pre-computed assessment.
- Devpost page, architecture diagrams, deployment configs (Vercel + Railway) created.
- Item 11 (digital twin) was built but checklist checkbox left unmarked — fixed during /iterate.
- Notable: Git `lib/` pattern in `.gitignore` required `git add -f` for frontend 3D lib files.
<<<<<<< HEAD
<<<<<<< HEAD
- Deployment: migrated from Vercel+Railway to OCI Always Free Tier (Ampere A1 Flex VM). See `docker-compose.prod.yml`, `Caddyfile`, `infrastructure/terraform/`.
- FreeCAD CAD export: blocked on ARM64 (no `freecad-python3` ARM build). Feature flag `enable_cad_export=False`, not deployed.
=======
- Deployment: not yet live on Vercel/Railway — configs are placeholder-ready.
>>>>>>> origin/main
=======
- Deployment: not yet live on Vercel/Railway — configs are placeholder-ready.
>>>>>>> origin/main

## /iterate
