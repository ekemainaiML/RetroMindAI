# RetroMind AI - Product Requirements

## Problem Statement
Independent EV retrofit workshops in India repeatedly perform high-stakes engineering decisions on imperfect vehicles (damaged, modified, undocumented) using inconsistent manual workflows and tribal knowledge. This creates slower turnaround, uneven safety quality, and poor standardization across jobs. RetroMind AI must provide a workshop-first, trust-building assessment and recommendation flow that tolerates messy real-world inputs while delivering adaptive, confidence-aware retrofit decisions fast enough for daily operations.

## User Stories

### Epic: Guided First-Run Retrofit Intake

- As a retrofit workshop operator, I want to start a new retrofit immediately on first open so that I can get value in seconds without setup friction.
  - [ ] First screen presents a focused guided engineering workspace, not a dense analytics dashboard.
  - [ ] A primary call-to-action to start a retrofit is visually dominant and unambiguous.
  - [ ] The page clearly states what outcomes the workflow will produce (assessment, feasibility, adaptive recommendation, safety-oriented output).
  - [ ] Edge case: if no prior retrofits exist, the system shows helpful first-run guidance rather than an empty management view.

- As a retrofit workshop operator, I want guided photo capture slots so that I know exactly what evidence is needed for accurate assessment.
  - [ ] Upload workflow requests front, left, right, rear, and engine/battery bay views.
  - [ ] Underbody input is marked optional and does not block baseline analysis.
  - [ ] Each required view has capture guidance (what angle/coverage is expected).
  - [ ] Edge case: missing required views trigger recovery guidance and a continue-with-limited-analysis path.

### Epic: Vehicle Intelligence and Deviation Detection

- As a retrofit workshop operator, I want the system to identify vehicle class and structural context from uploaded evidence so that I can trust that analysis is grounded in the actual vehicle.
  - [ ] System returns a detected vehicle class with a visible confidence value.
  - [ ] System surfaces structural context summary (for example geometry quality and notable anomaly regions).
  - [ ] If classification is uncertain, system asks for explicit user confirmation before proceeding with final outputs.
  - [ ] Edge case: contradictory evidence is resolved through human-in-the-loop confirmation.

- As a retrofit workshop operator, I want the system to detect real-world deviations (not just ideal conditions) so that recommendations are safe for imperfect vehicles.
  - [ ] Output explicitly flags detected deviations (for example asymmetry, weld modifications, visibility gaps).
  - [ ] Deviations are tied to recommendation impact (what changed because of the detected issue).
  - [ ] Detected issues are grouped into understandable severity language.
  - [ ] Edge case: low-confidence deviation detection is labeled as tentative rather than definitive.

### Epic: Feasibility and Risk Decisioning

- As a retrofit workshop operator, I want a fast feasibility assessment so that I can quickly decide whether conversion is viable before deeper work.
  - [ ] First feasibility result appears within 60 seconds under normal conditions.
  - [ ] First feasibility result never exceeds 2 minutes maximum for initial assessment.
  - [ ] Result includes a numeric feasibility score and plain-language recommendation (for example feasible, constrained feasible, not currently safe).
  - [ ] Edge case: when critical visibility is missing, system withholds unsafe recommendation and explains exactly what must be added.

- As a retrofit workshop operator, I want risk and confidence to be explicit so that I understand how much to trust each decision.
  - [ ] Assessment displays a visible confidence score alongside feasibility.
  - [ ] Confidence reduction includes explicit reason codes (for example missing view, blur, occlusion).
  - [ ] Risk summary identifies top safety constraints in plain language.
  - [ ] Edge case: if confidence falls below safe threshold, output switches to caution mode with required next actions.

### Epic: Adaptive Retrofit Recommendations

- As a retrofit workshop operator, I want deviation-aware battery placement recommendations so that unsafe standard layouts are automatically adjusted.
  - [ ] Recommendation output shows baseline risk and adapted recommendation.
  - [ ] System explicitly states why adaptation was made (for example frame asymmetry compensation).
  - [ ] Recommendation includes clear placement zones and key constraints.
  - [ ] Edge case: if no safe placement can be recommended from available evidence, system reports "cannot recommend safely yet" with required additional evidence.

- As a retrofit workshop operator, I want intelligent wiring guidance so that I can reduce avoidable routing and safety mistakes.
  - [ ] Output provides a proposed routing direction with highlighted caution zones.
  - [ ] Output identifies known risk areas relevant to the specific vehicle assessment.
  - [ ] Recommendation language is operational and workshop-readable.
  - [ ] Edge case: if structural visibility is limited, wiring guidance is labeled partial with confidence reduction.

### Epic: Graceful Degradation and Guided Recovery

- As a retrofit workshop operator, I want the system to continue analysis when possible (instead of hard-failing) so that workshop flow is not blocked by imperfect inputs.
  - [ ] Missing required inputs trigger two clear choices: upload missing evidence or continue with limited analysis.
  - [ ] Blurry or low-quality images trigger retake recommendation plus a continue option.
  - [ ] Incomplete evidence automatically reduces confidence and logs the reason.
  - [ ] Edge case: only safety-critical insufficiency triggers hard block.

- As a retrofit workshop operator, I want intelligent recovery for common upload mistakes so that I can correct issues quickly.
  - [ ] Suspected left/right mismatch is detected and presented with auto-correct plus user confirmation.
  - [ ] Low-light inputs are auto-enhanced before analysis and flagged as enhanced.
  - [ ] Occlusion is highlighted with guidance on what to recapture.
  - [ ] Edge case: if enhancement still fails minimum interpretability, system downgrades confidence and requests targeted retake.

### Epic: Progressive Insight and Explainability

- As a retrofit workshop operator, I want staged progress updates so that I see trustworthy insight quickly instead of waiting for one opaque final response.
  - [ ] Workflow shows progress milestones (vehicle identified, structural scan, feasibility, adaptive recommendation, advanced views).
  - [ ] Each milestone renders user-visible output as it becomes available.
  - [ ] Progress messaging communicates what is complete vs still running.
  - [ ] Edge case: if a stage fails, prior completed stages remain visible with failure explanation for the next stage.

- As a retrofit workshop operator, I want a visual explanation layer so that engineering decisions feel inspectable, not black-box.
  - [ ] Result view includes a simplified vehicle visualization with highlighted anomaly and recommendation zones.
  - [ ] Visual overlays align with textual findings and do not contradict assessment summaries.
  - [ ] User can identify which detected issue influenced which recommendation.
  - [ ] Edge case: when confidence is low, visualization includes uncertainty cues.

### Epic: Retrofit Intelligence Continuity

- As a retrofit workshop operator, I want each retrofit to leave a reusable intelligence trail so that future retrofits improve over time.
  - [ ] Each completed assessment records a structured retrofit intelligence record (Retrofit DNA summary).
  - [ ] Result view includes a visible note that prior similar outcomes can influence recommendations.
  - [ ] Operator can access prior retrofit entries from the workspace.
  - [ ] Edge case: if no similar prior entries exist, system indicates "new pattern" instead of implying prior evidence.

## What We're Building
- Guided first-run workspace that prioritizes immediate retrofit start over admin/dashboard complexity.
- Structured upload and first-pass validation with required/optional evidence handling.
- Fast feasibility decisioning with explicit timing targets (target <=60s, hard max 2 min for first result).
- Deviation-aware recommendation behavior as core product promise (not generic recommendation output).
- Confidence-first UX across all outputs, including reason codes and caution states.
- Graceful degradation for messy workshop inputs with guided recovery and minimal hard blocks.
- Progressive insight pipeline that reveals value in stages instead of one delayed final response.
- Explainable visual summary layer that links detected issues to recommendation changes.
- Retrofit DNA continuity in the user-visible workflow so learning value is demonstrable.

## What We'd Add With More Time
No additional deferred feature bucket is defined at this stage. The learner explicitly chose full inclusion of all discussed requirement areas for the hackathon submission scope, with depth managed through execution quality and progressive delivery.

## Non-Goals
- Passenger car-first launch behavior is out of scope for initial launch wedge, because it materially increases variability and slows validation of the core workshop workflow.
- OEM-first go-to-market workflow is out of scope for this phase, because enterprise procurement/validation flows are not required to prove workshop product value.
- Fleet-first onboarding and operations workflows are out of scope for initial release, because workshop intelligence proof comes first.
- Generic analytics-heavy landing dashboard is out of scope for first run, because it delays trust-building time-to-value.
- Binary validator behavior that blocks non-critical input issues is out of scope, because real workshop environments require tolerant, confidence-aware operation.

## Open Questions
- What exact confidence thresholds map to "full confidence," "reduced confidence," "partial assessment," and "unsafe to assess" states? (Needs answer before /spec.)
- What is the minimum required evidence set for a hard safety block vs limited-analysis continuation for each supported vehicle class? (Needs answer before /spec.)
- Which risk labels and severity tiers should be standardized in the first release so operators see consistent language? (Needs answer before /spec.)
- Which compliance output fields are required in the first demo-ready report vs added later in deeper certification workflows? (Can be refined during /spec.)
