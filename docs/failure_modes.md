# RetroMind AI — Failure Modes & Graceful Degradation

## Categories

1. [Input Failures](#1-input-failures)
2. [AI Inference Failures](#2-ai-inference-failures)
3. [Async Job Failures](#3-async-job-failures)
4. [Infrastructure Failures](#4-infrastructure-failures)
5. [Safety/Recommendation Failures](#5-safetyrecommendation-failures)
6. [UX Edge Cases](#6-ux-edge-cases)
7. [Concurrency & Recovery](#7-concurrency--recovery)
8. [Unsupported Vehicle Cases](#8-unsupported-vehicle-cases)

---

## Template

Each entry:

| Field | Description |
|-------|-------------|
| **ID** | Unique identifier (FM-{CAT}-{NN}) |
| **Category** | Failure mode category |
| **Failure Mode** | What goes wrong |
| **Trigger** | Conditions that cause failure |
| **Detection** | How the system recognizes it |
| **Fallback Behavior** | What the system does |
| **User Message** | What the operator sees |
| **Assessment Impact** | Effect on confidence/state |
| **Blocking Rules** | Whether recommendations are blocked |
| **Telemetry Logged** | Structured data recorded |
| **Recovery Path** | How to resolve |
| **Acceptance Criteria** | Testable pass condition |

---

## 1. Input Failures

### FM-IN-01: Missing Mandatory View

| Field | Value |
|-------|-------|
| **ID** | FM-IN-01 |
| **Category** | Input Failures |
| **Failure Mode** | 1 of 3 mandatory views not submitted at intake |
| **Trigger** | Intake submitted without `left_side_profile`, `right_side_profile`, or `rear_view` |
| **Detection** | Intake validation counts submitted slots against mandatory set |
| **Fallback Behavior** | Prompt operator to upload missing view; offer continue-with-limited-analysis path |
| **User Message** | "Rear view not submitted. Upload now or continue with limited analysis." |
| **Assessment Impact** | 2/3 mandatory valid -> `partial_assessment`; <2 -> `unsafe_to_assess` |
| **Blocking Rules** | `unsafe_to_assess` blocks all recommendations |
| **Telemetry Logged** | `missing_mandatory_view`, `attempt_count`, `resolution` |
| **Recovery Path** | Upload missing view; system re-validates and re-triggers analysis |
| **Acceptance Criteria** | Given incomplete intake, when operator chooses to continue, system SHALL downgrade to `partial_assessment` and SHALL NOT generate recommendations |

### FM-IN-02: Repeated Upload Failure (3 Attempts)

| Field | Value |
|-------|-------|
| **ID** | FM-IN-02 |
| **Category** | Input Failures |
| **Failure Mode** | Same mandatory view fails validation 3 times |
| **Trigger** | Per-view attempt counter reaches 3 |
| **Detection** | Per-view upload retry counter monitored during intake |
| **Fallback Behavior** | Force `unsafe_to_assess`; stop recommendation generation |
| **User Message** | "Unable to obtain a usable view after 3 attempts. Assessment cannot proceed safely." |
| **Assessment Impact** | `unsafe_to_assess` irrespective of other scores |
| **Blocking Rules** | All recommendations blocked |
| **Telemetry Logged** | `max_retry_exceeded`, `view_slot`, `failure_reasons[]` |
| **Recovery Path** | Start new intake with different capture conditions/equipment |
| **Acceptance Criteria** | Given 3 failed attempts for one mandatory view, system SHALL set state to `unsafe_to_assess` and SHALL NOT generate recommendations |

### FM-IN-03: Blurry / Low-Quality Image

| Field | Value |
|-------|-------|
| **ID** | FM-IN-03 |
| **Category** | Input Failures |
| **Failure Mode** | Image quality score below threshold |
| **Trigger** | Quality score < 0.4 on Laplacian variance or quality classifier |
| **Detection** | OpenCV blur detection or quality model |
| **Fallback Behavior** | Flag as low quality; offer retake; allow continue with downgrade |
| **User Message** | "Left side view appears blurry. This will reduce assessment accuracy. Re-upload or continue with reduced confidence." |
| **Assessment Impact** | Quality factor reduced; confidence score adjusted |
| **Blocking Rules** | Non-blocking unless it affects mandatory view count |
| **Telemetry Logged** | `low_quality_view`, `view_slot`, `quality_score`, `resolution` |
| **Recovery Path** | Re-upload clearer image; system re-runs quality check |
| **Acceptance Criteria** | Given blurry image, when operator continues without retake, system SHALL reduce confidence and SHALL log reason code |

### FM-IN-04: Left/Right View Swap

| Field | Value |
|-------|-------|
| **ID** | FM-IN-04 |
| **Category** | Input Failures |
| **Failure Mode** | Left image uploaded to right slot or vice versa |
| **Trigger** | Mirror symmetry detection or orientation classifier flags mismatch |
| **Detection** | Orientation/symmetry model during image quality stage |
| **Fallback Behavior** | Auto-correct + human confirmation prompt |
| **User Message** | "Left and right views appear swapped. Auto-correct applied. Please confirm: [ Accept Correction ] [ Swap Manually ]" |
| **Assessment Impact** | None if confirmed; re-analysis if corrected |
| **Blocking Rules** | Non-blocking |
| **Telemetry Logged** | `view_swap_detected`, `auto_correct_applied`, `operator_confirmed` |
| **Recovery Path** | Operator confirms or rejects correction |
| **Acceptance Criteria** | Given suspected left/right swap, system SHALL auto-correct and SHALL prompt for confirmation before proceeding |

### FM-IN-05: Low-Light Input

| Field | Value |
|-------|-------|
| **ID** | FM-IN-05 |
| **Category** | Input Failures |
| **Failure Mode** | Image mean pixel brightness below exposure threshold |
| **Trigger** | Mean brightness < threshold |
| **Detection** | Histogram analysis or exposure classifier |
| **Fallback Behavior** | Auto-enhance before analysis; flag as enhanced |
| **User Message** | "Low light detected. Image auto-enhanced for analysis." |
| **Assessment Impact** | Quality factor may be reduced; `enhanced` flag on view |
| **Blocking Rules** | Non-blocking |
| **Telemetry Logged** | `low_light_detected`, `enhancement_applied` |
| **Recovery Path** | Optional re-upload under better lighting |
| **Acceptance Criteria** | Given low-light input, system SHALL auto-enhance and SHALL flag the enhancement in assessment output |

### FM-IN-06: Occlusion Detected

| Field | Value |
|-------|-------|
| **ID** | FM-IN-06 |
| **Category** | Input Failures |
| **Failure Mode** | Object obstructs critical vehicle structure |
| **Trigger** | Segmentation or object detection model finds occlusion (tarp, person, etc.) |
| **Detection** | Object detection / segmentation during quality stage |
| **Fallback Behavior** | Highlight occlusion region; flag as reduced visibility; request targeted retake |
| **User Message** | "Occlusion detected in rear view (upper left quadrant). Please recapture with clear visibility." |
| **Assessment Impact** | Visibility factor reduced for affected view |
| **Blocking Rules** | Non-blocking unless it degrades mandatory view below usability threshold |
| **Telemetry Logged** | `occlusion_detected`, `view_slot`, `region`, `coverage_pct` |
| **Recovery Path** | Re-upload unobstructed image |
| **Acceptance Criteria** | Given occlusion in mandatory view, system SHALL flag the affected region and SHALL request targeted retake |

---

## 2. AI Inference Failures

### FM-AI-01: Low Classification Confidence (Recoverable)

| Field | Value |
|-------|-------|
| **ID** | FM-AI-01 |
| **Category** | AI Inference Failures |
| **Failure Mode** | Classification confidence 50-84 or moderate geometry conflict |
| **Trigger** | Confidence engine detects ambiguity; alternative predictions within 30% margin |
| **Detection** | Classification stage output + geometry consistency check |
| **Fallback Behavior** | Human confirmation prompt with constrained options |
| **User Message** | "Vehicle classification uncertain. Detected: Three-Wheeler (58%) / Motorcycle (31%). Please confirm." |
| **Assessment Impact** | Eligible for `full_confidence` or `reduced_confidence` after confirmation; `human_confirmed` tag |
| **Blocking Rules** | Non-blocking; pending operator input (60s timeout) |
| **Telemetry Logged** | `classification_ambiguity`, `top_candidates[]`, `operator_selection`, `human_confirmed` |
| **Recovery Path** | Operator selects from options or re-uploads |
| **Acceptance Criteria** | Given recoverable classification ambiguity, system SHALL surface confirmation prompt with constrained input, SHALL record override, SHALL increase effective confidence |

### FM-AI-02: Unresolved Model Conflict

| Field | Value |
|-------|-------|
| **ID** | FM-AI-02 |
| **Category** | AI Inference Failures |
| **Failure Mode** | Operator skips or timeout expires; conflict persists |
| **Trigger** | Confirmation timeout (60s without response) or conflict re-detected after input |
| **Detection** | Confirmation endpoint not called within window; or conflict flag persists |
| **Fallback Behavior** | Auto-downgrade to `partial_assessment` |
| **User Message** | "Vehicle classification could not be confirmed. Continuing with partial assessment." |
| **Assessment Impact** | `partial_assessment`; reason code `unresolved_model_conflict` |
| **Blocking Rules** | Preliminary feasibility only; strong recommendations blocked |
| **Telemetry Logged** | `unresolved_model_conflict`, `reason`, `state_downgraded`, `final_state` |
| **Recovery Path** | Start new intake with clearer images |
| **Acceptance Criteria** | Given unresolved conflict after operator timeout, system SHALL downgrade to `partial_assessment` and SHALL limit recommendations to preliminary guidance |

### FM-AI-03: Severe Classification Contradiction

| Field | Value |
|-------|-------|
| **ID** | FM-AI-03 |
| **Category** | AI Inference Failures |
| **Failure Mode** | Classifier confidence < 40 AND geometry consistency < 40 AND mandatory views weak |
| **Trigger** | Confidence engine detects critical-level contradiction |
| **Detection** | Multi-factor threshold check post-inference |
| **Fallback Behavior** | Safety override; no human prompt; force `unsafe_to_assess` |
| **User Message** | "RetroMind cannot safely assess this vehicle. The available evidence contains critical inconsistencies. Please upload clearer images from all mandatory views." |
| **Assessment Impact** | `unsafe_to_assess`; no recommendations |
| **Blocking Rules** | All recommendations blocked |
| **Telemetry Logged** | `severe_contradiction`, `classifier_conf`, `geometry_conf`, `view_quality`, `triggered_override` |
| **Recovery Path** | Start new intake with better evidence |
| **Acceptance Criteria** | Given classifier confidence < 40 AND geometry consistency < 40 AND weak mandatory views, system SHALL force `unsafe_to_assess` without human prompt |

### FM-AI-04: Model Load Failure

| Field | Value |
|-------|-------|
| **ID** | FM-AI-04 |
| **Category** | AI Inference Failures |
| **Failure Mode** | ONNX/PyTorch model fails to load or returns runtime error |
| **Trigger** | Worker exception on model initialization |
| **Detection** | Exception caught during worker startup or inference call |
| **Fallback Behavior** | Return error with specific model name; allow retry |
| **User Message** | "A core analysis component could not be loaded. Please retry." |
| **Assessment Impact** | Job fails; no assessment |
| **Blocking Rules** | All recommendations blocked (Tier 0 infra) |
| **Telemetry Logged** | `model_load_failure`, `model_name`, `error_message` |
| **Recovery Path** | Retry (worker restart); escalate if persistent |
| **Acceptance Criteria** | Given model load failure, system SHALL return clear error with affected model name and SHALL allow retry |

---

## 3. Async Job Failures

### FM-AJ-01: Soft Timeout Warning (90s)

| Field | Value |
|-------|-------|
| **ID** | FM-AJ-01 |
| **Category** | Async Job Failures |
| **Failure Mode** | Job exceeds 90s execution time |
| **Trigger** | Duration counter reaches 90s |
| **Detection** | RQ job monitoring timer |
| **Fallback Behavior** | UI warning; no interruption |
| **User Message** | "Analysis is taking longer than expected. RetroMind is continuing structural analysis..." |
| **Assessment Impact** | None yet |
| **Blocking Rules** | None |
| **Telemetry Logged** | `soft_timeout_warning`, `current_stage`, `elapsed_seconds` |
| **Recovery Path** | Automatic; system continues processing |
| **Acceptance Criteria** | Given job exceeds 90s, system SHALL surface UI warning and SHALL NOT interrupt processing |

### FM-AJ-02: Hard Timeout (120s)

| Field | Value |
|-------|-------|
| **ID** | FM-AJ-02 |
| **Category** | Async Job Failures |
| **Failure Mode** | Job exceeds 120s hard time limit |
| **Trigger** | Duration counter reaches 120s |
| **Detection** | Hard timeout monitor in job orchestrator |
| **Fallback Behavior** | Terminate worker; persist completed stages; evaluate for partial results |
| **User Message** | See FM-AJ-03 or FM-AJ-04 depending on partial result availability |
| **Assessment Impact** | Depends on completed stages |
| **Blocking Rules** | Depends on resulting assessment state |
| **Telemetry Logged** | `hard_timeout`, `completed_stages[]`, `missing_stages[]`, `meaningful_partial` |
| **Recovery Path** | Auto-retry once if recoverable (see FM-AJ-05) |
| **Acceptance Criteria** | Given job exceeds 120s, system SHALL terminate, SHALL persist completed stages, and SHALL evaluate for meaningful partial result |

### FM-AJ-03: Meaningful Partial Result Available

| Field | Value |
|-------|-------|
| **ID** | FM-AJ-03 |
| **Category** | Async Job Failures |
| **Failure Mode** | Hard timeout hit; minimum viable stages completed |
| **Trigger** | Hard timeout AND completed stages >= `vehicle_classification` + `geometry_extraction` + `deviation_detection` |
| **Detection** | Post-timeout evaluation of completed stage set |
| **Fallback Behavior** | Return `partial_complete` with available results |
| **User Message** | "RetroMind completed a preliminary assessment. Advanced optimization timed out. Available: Feasibility, Structural findings, Risk analysis. Unavailable: Battery optimization, Wiring recommendation. [ Retry Advanced Analysis ]" |
| **Assessment Impact** | `partial_assessment` or `reduced_confidence` |
| **Blocking Rules** | Strong recommendations blocked; preliminary feasibility allowed |
| **Telemetry Logged** | `partial_result_returned`, `completed_stages[]`, `missing_stages[]` |
| **Recovery Path** | Retry advanced analysis; resumes from last completed stage |
| **Acceptance Criteria** | Given hard timeout with meaningful partial results, system SHALL return `partial_complete` status with completed/missing stages and SHALL allow retry |

### FM-AJ-04: No Meaningful Partial Result

| Field | Value |
|-------|-------|
| **ID** | FM-AJ-04 |
| **Category** | Async Job Failures |
| **Failure Mode** | Hard timeout hit; insufficient stages completed |
| **Trigger** | Hard timeout AND completed stages < `vehicle_classification` + `geometry_extraction` + `deviation_detection` |
| **Detection** | Post-timeout evaluation of completed stage set |
| **Fallback Behavior** | Return `unsafe_to_assess`; no retry available |
| **User Message** | "RetroMind could not complete sufficient analysis within the allowed processing window. Please retry or upload clearer images." |
| **Assessment Impact** | `unsafe_to_assess` |
| **Blocking Rules** | All recommendations blocked |
| **Telemetry Logged** | `no_meaningful_partial`, `completed_stages[]` |
| **Recovery Path** | New intake with clearer images |
| **Acceptance Criteria** | Given hard timeout without meaningful partial results, system SHALL return `unsafe_to_assess` and SHALL NOT offer retry |

### FM-AJ-05: Auto-Retry (Recoverable Timeout)

| Field | Value |
|-------|-------|
| **ID** | FM-AJ-05 |
| **Category** | Async Job Failures |
| **Failure Mode** | Hard timeout occurred; retry count = 0; reason was recoverable |
| **Trigger** | Hard timeout AND retry_count == 0 AND reason is transient (compute spike, worker hiccup, ONNX stall) |
| **Detection** | Job orchestrator evaluates timeout reason from telemetry |
| **Fallback Behavior** | Enqueue job for retry; status -> `retrying` |
| **User Message** | "Analysis taking longer than expected. RetroMind is retrying automatically." |
| **Assessment Impact** | None; pending retry completion |
| **Blocking Rules** | Pending |
| **Telemetry Logged** | `auto_retry`, `attempt_number`, `original_timeout_reason` |
| **Recovery Path** | Automatic; worker resumes from last completed stage |
| **Acceptance Criteria** | Given recoverable timeout with retry available, system SHALL auto-retry once and SHALL NOT require user action |

### FM-AJ-06: Retry Also Fails

| Field | Value |
|-------|-------|
| **ID** | FM-AJ-06 |
| **Category** | Async Job Failures |
| **Failure Mode** | Auto-retry also exceeds hard timeout |
| **Trigger** | Hard timeout on retry attempt (retry_count > 0) |
| **Detection** | Same timeout monitor; retry count > 0 |
| **Fallback Behavior** | Apply partial result logic (FM-AJ-03 or FM-AJ-04); no further retry |
| **User Message** | Same as FM-AJ-03 or FM-AJ-04 |
| **Assessment Impact** | Same as FM-AJ-03 or FM-AJ-04 |
| **Blocking Rules** | Same as FM-AJ-03 or FM-AJ-04 |
| **Telemetry Logged** | `retry_failed`, `completed_stages[]`, `missing_stages[]`, `meaningful_partial` |
| **Recovery Path** | New intake |
| **Acceptance Criteria** | Given retry failure, system SHALL NOT auto-retry again and SHALL fall back to partial result or `unsafe_to_assess` decision |

---

## 4. Infrastructure Failures

### FM-IF-01: PostgreSQL Unavailable (Tier 0)

| Field | Value |
|-------|-------|
| **ID** | FM-IF-01 |
| **Category** | Infrastructure Failures |
| **Failure Mode** | Database connection fails or query timeout |
| **Trigger** | Connection pool exhaustion, network error, PG crash |
| **Detection** | API/worker health check; connection error |
| **Fallback Behavior** | Hard fail; no graceful path |
| **User Message** | "RetroMind is temporarily unavailable. Assessment data could not be safely persisted. Please retry shortly." |
| **Assessment Impact** | Hard fail; `unsafe_to_assess` |
| **Blocking Rules** | All blocked |
| **Telemetry Logged** | `postgres_unavailable`, `error_details`, `timestamp` |
| **Recovery Path** | Restore PostgreSQL connection; retry |
| **Acceptance Criteria** | Given PostgreSQL unavailable, system SHALL fail all jobs and SHALL NOT proceed with assessment |

### FM-IF-02: Redis/RQ Unavailable (Tier 0)

| Field | Value |
|-------|-------|
| **ID** | FM-IF-02 |
| **Category** | Infrastructure Failures |
| **Failure Mode** | Redis connection fails or RQ broker unreachable |
| **Trigger** | Redis connection error, RQ worker cannot poll |
| **Detection** | Worker health check; RQ connection error |
| **Fallback Behavior** | Hard fail; no async execution possible |
| **User Message** | "RetroMind is temporarily unavailable. The analysis queue cannot be started. Please retry shortly." |
| **Assessment Impact** | Hard fail; no jobs can be queued |
| **Blocking Rules** | All blocked |
| **Telemetry Logged** | `redis_unavailable`, `queue_unavailable`, `timestamp` |
| **Recovery Path** | Restore Redis; restart worker |
| **Acceptance Criteria** | Given Redis/RQ unavailable, system SHALL reject job creation requests with 503 |

### FM-IF-03: Core Inference Runtime Unavailable (Tier 0)

| Field | Value |
|-------|-------|
| **ID** | FM-IF-03 |
| **Category** | Infrastructure Failures |
| **Failure Mode** | ONNX/PyTorch runtime fails or model server unreachable |
| **Trigger** | Worker exception during model load or inference |
| **Detection** | Exception caught during worker execution |
| **Fallback Behavior** | Hard fail |
| **User Message** | "A core analysis component could not be loaded. Please retry." |
| **Assessment Impact** | Hard fail; job marked failed |
| **Blocking Rules** | All blocked |
| **Telemetry Logged** | `inference_runtime_failure`, `model_name`, `error` |
| **Recovery Path** | Restart worker or restore model artifacts |
| **Acceptance Criteria** | Given core inference runtime unavailable, system SHALL fail the active job and SHALL return clear error |

### FM-IF-04: Neo4j Unavailable (Tier 1)

| Field | Value |
|-------|-------|
| **ID** | FM-IF-04 |
| **Category** | Infrastructure Failures |
| **Failure Mode** | Graph database connection fails |
| **Trigger** | Neo4j connection error or query timeout |
| **Detection** | API/worker health check; Neo4j driver error |
| **Fallback Behavior** | Graceful degradation; fall back to heuristic recommendation engine |
| **User Message** | "Retrofit intelligence memory temporarily unavailable. Recommendations generated without historical retrofit benchmarking." |
| **Assessment Impact** | `reduced_confidence` or `partial_assessment`; `infrastructure_degradation` entry logged |
| **Blocking Rules** | Non-blocking |
| **Telemetry Logged** | `neo4j_unavailable`, `fallback_engine`, `timestamp` |
| **Recovery Path** | Restore Neo4j connection; next job resumes graph intelligence |
| **Acceptance Criteria** | Given Neo4j unavailable, system SHALL continue assessment using heuristic fallback, SHALL record degradation, and SHALL inform operator |

### FM-IF-05: Cloudflare R2 Unavailable (Tier 1)

| Field | Value |
|-------|-------|
| **ID** | FM-IF-05 |
| **Category** | Infrastructure Failures |
| **Failure Mode** | Object storage put/get fails |
| **Trigger** | S3 client error or timeout |
| **Detection** | S3 client exception during upload/retrieve |
| **Fallback Behavior** | Use temporary local storage (in-memory or ephemeral disk); retry persistence |
| **User Message** | "Media persistence temporarily degraded. Assessment completed with limited storage reliability." |
| **Assessment Impact** | `reduced_confidence` if retry fails; otherwise no impact |
| **Blocking Rules** | Non-blocking |
| **Telemetry Logged** | `r2_unavailable`, `fallback_storage`, `persistence_retry_count` |
| **Recovery Path** | Restore R2 connectivity; background sync of temp data |
| **Acceptance Criteria** | Given R2 unavailable, system SHALL fall back to local storage and SHALL continue assessment |

### FM-IF-06: Battery Optimizer Unavailable (Tier 1)

| Field | Value |
|-------|-------|
| **ID** | FM-IF-06 |
| **Category** | Infrastructure Failures |
| **Failure Mode** | Optimization engine fails or exceeds sub-timeout |
| **Trigger** | Worker exception in optimization stage or stage-specific timeout |
| **Detection** | Exception or timeout in battery_optimization stage |
| **Fallback Behavior** | Return assessment without optimization; flag as missing stage |
| **User Message** | "Advanced optimization timed out. Feasibility and risk assessment completed." |
| **Assessment Impact** | `partial_assessment` or `reduced_confidence`; `battery_optimization` in `missing_stages` |
| **Blocking Rules** | Strong battery recommendations blocked; preliminary feasibility available |
| **Telemetry Logged** | `optimizer_unavailable`, `completed_stages[]`, `missing_stages[]` |
| **Recovery Path** | Retry advanced analysis |
| **Acceptance Criteria** | Given battery optimizer unavailable, system SHALL return partial results and SHALL allow retry |

### FM-IF-07: Digital Twin Generator Unavailable (Tier 1)

| Field | Value |
|-------|-------|
| **ID** | FM-IF-07 |
| **Category** | Infrastructure Failures |
| **Failure Mode** | 3D visualization engine fails |
| **Trigger** | Worker exception in digital_twin stage |
| **Detection** | Exception caught during digital twin generation |
| **Fallback Behavior** | Skip stage; complete assessment without visualization |
| **User Message** | "Digital twin visualization unavailable. Core retrofit assessment completed successfully." |
| **Assessment Impact** | None on core assessment |
| **Blocking Rules** | Non-blocking |
| **Telemetry Logged** | `digital_twin_unavailable`, `stage_skipped` |
| **Recovery Path** | Retry visualization separately |
| **Acceptance Criteria** | Given digital twin unavailable, system SHALL skip the stage and SHALL complete assessment without impact on core results |

---

## 5. Safety/Recommendation Failures

### FM-SR-01: Critical Risk Blocks Recommendation

| Field | Value |
|-------|-------|
| **ID** | FM-SR-01 |
| **Category** | Safety/Recommendation Failures |
| **Failure Mode** | One or more risks at `critical` severity |
| **Trigger** | Risk analysis stage identifies critical-severity finding |
| **Detection** | Risk severity check post-analysis |
| **Fallback Behavior** | Block all recommendations; report `unsafe_to_recommend` |
| **User Message** | "A critical safety issue was detected. RetroMind cannot recommend conversion safely until resolved." |
| **Assessment Impact** | Recommendation status = `unsafe_to_recommend` |
| **Blocking Rules** | All recommendations blocked |
| **Telemetry Logged** | `critical_risk_blocked`, `risk_id`, `risk_category`, `risk_message` |
| **Recovery Path** | Address critical risk and re-assess |
| **Acceptance Criteria** | Given a critical-severity risk, system SHALL block all recommendations and SHALL set recommendation status to `unsafe_to_recommend` |

### FM-SR-02: High Risk Escalation (>=3 High Risks)

| Field | Value |
|-------|-------|
| **ID** | FM-SR-02 |
| **Category** | Safety/Recommendation Failures |
| **Failure Mode** | 3 or more `high` severity risks detected |
| **Trigger** | Risk aggregation finds >=3 high-severity items |
| **Detection** | Risk aggregation at end of risk analysis stage |
| **Fallback Behavior** | Escalate system risk state to critical; block recommendations |
| **User Message** | "Multiple significant risks detected. RetroMind cannot recommend conversion until the top risks are addressed." |
| **Assessment Impact** | System risk state -> critical; recommendations blocked |
| **Blocking Rules** | All recommendations blocked |
| **Telemetry Logged** | `high_risk_escalation`, `high_count`, `critical_system_risk`, `risk_ids[]` |
| **Recovery Path** | Mitigate high-severity risks below escalation threshold; re-assess |
| **Acceptance Criteria** | Given 3+ high risks, system SHALL escalate to critical system risk state and SHALL block recommendations |

### FM-SR-03: No Safe Battery Placement

| Field | Value |
|-------|-------|
| **ID** | FM-SR-03 |
| **Category** | Safety/Recommendation Failures |
| **Failure Mode** | Optimization engine finds zero valid battery placement zones |
| **Trigger** | Constraint solver returns empty solution set |
| **Detection** | Empty solution set from optimization |
| **Fallback Behavior** | Report "cannot recommend safely yet" with required additional evidence |
| **User Message** | "RetroMind could not identify a safe battery placement zone. Additional structural evidence is required." |
| **Assessment Impact** | Recommendation status -> `unsafe_to_recommend` for battery; other recommendations may continue |
| **Blocking Rules** | Battery placement blocked; other recommendations may proceed |
| **Telemetry Logged** | `no_safe_placement`, `constraints_evaluated`, `required_evidence[]` |
| **Recovery Path** | Provide additional structural evidence (underbody view, internal frame images) |
| **Acceptance Criteria** | Given no valid battery placement found, system SHALL report specific missing evidence and SHALL NOT recommend a placement |

---

## 6. UX Edge Cases

### FM-UX-01: Rapid Re-Uploads

| Field | Value |
|-------|-------|
| **ID** | FM-UX-01 |
| **Category** | UX Edge Cases |
| **Failure Mode** | Same view slot uploaded multiple times within short window |
| **Trigger** | Multiple uploads to same slot within 5s |
| **Detection** | Per-slot upload timestamp monitoring |
| **Fallback Behavior** | Accept latest valid upload; apply UI debounce (1-2s); re-trigger analysis |
| **User Message** | "New photo received. RetroMind is updating analysis..." |
| **Assessment Impact** | Intake state updated; re-analysis triggered if analysis already running |
| **Blocking Rules** | Non-blocking |
| **Telemetry Logged** | `rapid_reupload`, `view_slot`, `upload_count` |
| **Recovery Path** | Automatic; analysis restarts from appropriate stage |
| **Acceptance Criteria** | Given rapid re-uploads to same slot, system SHALL accept latest valid file and SHALL restart analysis without error |

### FM-UX-02: Tab Close / Browser Refresh

| Field | Value |
|-------|-------|
| **ID** | FM-UX-02 |
| **Category** | UX Edge Cases |
| **Failure Mode** | User closes tab, refreshes, or navigates away during active job |
| **Trigger** | Browser session ends (no client-side detection needed) |
| **Detection** | Server-side: no polling received; but job continues regardless |
| **Fallback Behavior** | Job continues server-side; results recoverable for 30 minutes |
| **User Message** | On return: "Assessment recovered. RetroMind continued processing while you were away. Current stage: Battery optimization (82%)." |
| **Assessment Impact** | None |
| **Blocking Rules** | None |
| **Telemetry Logged** | `session_interrupted`, `resume_ttl_start`, `job_id` |
| **Recovery Path** | Return to assessment page; state auto-restored |
| **Acceptance Criteria** | Given tab close during active job, system SHALL continue processing server-side, SHALL persist results for 30 minutes, and SHALL restore state on return |

### FM-UX-03: Concurrent Assessment Attempt

| Field | Value |
|-------|-------|
| **ID** | FM-UX-03 |
| **Category** | UX Edge Cases |
| **Failure Mode** | Operator starts new assessment while one is already active |
| **Trigger** | Active job count check finds existing running job |
| **Detection** | Job creation endpoint checks for existing active job per workshop |
| **Fallback Behavior** | Show current assessment status; offer cancel-and-start-new option |
| **User Message** | "An assessment is already running. Current: 3-Wheeler Intake #12 — Progress: 62%. [ View Current ] [ Cancel & Start New ]" |
| **Assessment Impact** | Existing job unaffected until cancelled |
| **Blocking Rules** | New job creation blocked |
| **Telemetry Logged** | `concurrent_attempt_blocked`, `active_job_id`, `workshop` |
| **Recovery Path** | Operator views existing or cancels and starts new |
| **Acceptance Criteria** | Given active job, when operator attempts new assessment, system SHALL block creation and SHALL offer current progress or cancel-and-start-new |

### FM-UX-04: Same-Intake Edit During Analysis

| Field | Value |
|-------|-------|
| **ID** | FM-UX-04 |
| **Category** | UX Edge Cases |
| **Failure Mode** | Operator replaces a view slot image while analysis is running |
| **Trigger** | Upload endpoint called for view that belongs to active intake with running job |
| **Detection** | Intake-job association check on upload |
| **Fallback Behavior** | Cancel stale downstream stages; restart analysis from appropriate point |
| **User Message** | "Photo updated. RetroMind is re-running analysis..." |
| **Assessment Impact** | Previous partial results invalidated; analysis restarts |
| **Blocking Rules** | Non-blocking |
| **Telemetry Logged** | `intake_edited_during_analysis`, `view_slot`, `stages_cancelled[]` |
| **Recovery Path** | Automatic; worker receives cancellation signal and re-enqueues |
| **Acceptance Criteria** | Given same-intake edit during active analysis, system SHALL cancel stale stages and SHALL restart analysis automatically |

---

## 7. Concurrency & Recovery

### FM-CR-01: 30-Minute Resume TTL Expiry

| Field | Value |
|-------|-------|
| **ID** | FM-CR-01 |
| **Category** | Concurrency & Recovery |
| **Failure Mode** | No poll received for >30 minutes since job completion |
| **Trigger** | TTL monitor finds job with last_access >30 min ago |
| **Detection** | Periodic TTL sweep in job orchestrator |
| **Fallback Behavior** | Mark job as expired; remove from active cache; retain in PostgreSQL |
| **User Message** | "This assessment session has expired. Please start a new assessment." |
| **Assessment Impact** | Job state -> expired (logical); data still available in PG |
| **Blocking Rules** | New assessment required |
| **Telemetry Logged** | `resume_ttl_expired`, `job_id`, `elapsed_minutes` |
| **Recovery Path** | Start new intake; reference prior assessment ID if needed |
| **Acceptance Criteria** | Given no activity for 30+ minutes, system SHALL expire the session and SHALL require new assessment |

### FM-CR-02: Worker Crash During Analysis

| Field | Value |
|-------|-------|
| **ID** | FM-CR-02 |
| **Category** | Concurrency & Recovery |
| **Failure Mode** | RQ worker process terminates unexpectedly |
| **Trigger** | OOM, unhandled exception, signal termination |
| **Detection** | RQ supervisor detects missing heartbeat; job remains in `running` state |
| **Fallback Behavior** | Mark job as `failed`; allow retry |
| **User Message** | "Analysis was interrupted unexpectedly. You can retry." |
| **Assessment Impact** | Job failed; no results |
| **Blocking Rules** | Pending retry |
| **Telemetry Logged** | `worker_crash`, `job_id`, `worker_id`, `last_stage` |
| **Recovery Path** | Operator retries; new worker picks up job from beginning (stage-level restart) |
| **Acceptance Criteria** | Given worker crash, system SHALL mark job as failed and SHALL allow operator retry |

---

## 8. Unsupported Vehicle Cases

### FM-UV-01: Unsupported Vehicle Class Detected

| Field | Value |
|-------|-------|
| **ID** | FM-UV-01 |
| **Category** | Unsupported Vehicle Cases |
| **Failure Mode** | Classification model returns vehicle type not in supported set |
| **Trigger** | Detected type not in v1 supported list (only 3-wheeler) |
| **Detection** | Post-classification validation against supported vehicle list |
| **Fallback Behavior** | Inform operator; offer limited structural analysis only |
| **User Message** | "RetroMind currently supports 3-wheeler conversions. The detected vehicle type is not yet supported. Limited structural analysis available." |
| **Assessment Impact** | `partial_assessment`; no conversion recommendations |
| **Blocking Rules** | All retrofit recommendations blocked; structural findings shown |
| **Telemetry Logged** | `unsupported_vehicle_class`, `detected_type`, `supported_set[]` |
| **Recovery Path** | None for v1; report recorded for training data |
| **Acceptance Criteria** | Given unsupported vehicle class, system SHALL inform operator, SHALL block recommendations, and SHALL offer limited structural findings |

### FM-UV-02: Classification Confidence Below Threshold (Unknown)

| Field | Value |
|-------|-------|
| **ID** | FM-UV-02 |
| **Category** | Unsupported Vehicle Cases |
| **Failure Mode** | Top classification confidence < 40 with no alternatives within range |
| **Trigger** | Max classification confidence < 40 |
| **Detection** | Classification stage output validation |
| **Fallback Behavior** | Report as unknown; request operator input |
| **User Message** | "RetroMind could not identify this vehicle type. Please specify: [ Three-Wheeler ] [ Motorcycle ] [ Unknown / Other ]" |
| **Assessment Impact** | `partial_assessment` pending operator input |
| **Blocking Rules** | Recommendations blocked until vehicle type confirmed |
| **Telemetry Logged** | `unknown_vehicle`, `top_confidence`, `alternatives[]`, `operator_input` |
| **Recovery Path** | Operator selects vehicle type; analysis continues with selected type |
| **Acceptance Criteria** | Given unknown vehicle (top conf < 40), system SHALL prompt operator for vehicle type and SHALL NOT proceed with recommendations until confirmed |

---

## Infrastructure Failure Tier Matrix

| Service | Tier | Behavior |
|---------|:----:|----------|
| FastAPI API | 0 | Hard fail |
| PostgreSQL | 0 | Hard fail |
| Redis / RQ | 0 | Hard fail |
| Core inference runtime | 0 | Hard fail |
| Neo4j Aura | 1 | Graceful degrade (heuristic fallback) |
| Cloudflare R2 | 1 | Graceful degrade (temp local storage) |
| Battery optimizer | 1 | Partial results; stage skipped |
| Wiring engine | 1 | Partial results; stage skipped |
| Digital twin | 1 | Skip stage |
| Report export | 2 | Silent graceful degrade |
| SSE (future) | 2 | Polling fallback |
| Analytics | 2 | Silent ignore |
| UI visual polish | 3 | Ignore |

**Tier 0 rule**: `recommendation_blocked = true`, `assessment_state = unsafe_to_assess`
**Tier 1 rule**: `partial_assessment` or `reduced_confidence`; continue; log degradation
**Tier 2+ rule**: silent degradation; no workflow interruption
