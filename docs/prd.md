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

### Epic: Enterprise 3D Digital Twin

- As a retrofit workshop operator, I want to see battery pack fitment visualized in 3D so that I can assess clearance before purchasing components.
  - [ ] Battery pack renders at the correct position with actual dimensions in the 3D scene.
  - [ ] Clearance zones (minimum distance to frame, heat sources, moving parts) are shown as wireframe bounding boxes.
  - [ ] Fitment status is color-coded: green (clear), yellow (tight), red (conflict).
  - [ ] Edge case: if no battery placement data exists, the fitment overlay is hidden.

- As a retrofit workshop operator, I want to measure distances directly in the 3D view so that I can answer spatial fit questions without manual measurement.
  - [ ] User can switch from orbit mode to measurement mode via a toolbar button.
  - [ ] Clicks in measurement mode place points with visible markers and show distance in mm.
  - [ ] Multiple segments can be chained; each shows its own distance.
  - [ ] Edge case: measurements clear on right-click or explicit clear button.

- As a retrofit workshop operator, I want heat sources visualized in the 3D scene so that I can plan battery and wiring placement away from hot zones.
  - [ ] Default heat zones (exhaust, engine bay) render as translucent colored spheres based on vehicle type.
  - [ ] Color gradient maps to temperature severity (green / yellow / red).
  - [ ] Deviation-triggered heat zones appear when damage notes mention heat or thermal issues.
  - [ ] Edge case: heat zones are toggleable and hidden by default.

- As a retrofit workshop operator, I want proposed wiring routes visualized in 3D so that I can plan HV cable routing before installation.
  - [ ] Wiring routes render as smooth 3D tubes/splines through waypoints from the battery to motor.
  - [ ] Caution zones along the route are highlighted in red/orange.
  - [ ] Route confidence is communicated via styling (solid for high confidence, dashed for low).
  - [ ] Edge case: if no wiring guidance exists, routes are hidden.

- As a retrofit workshop operator, I want to make the vehicle body transparent so that I can see internal component placement.
  - [ ] A slider control adjusts body panel opacity from 10% to 100%.
  - [ ] Internal components (battery, motor, controller) remain fully opaque at all times.
  - [ ] Deviation overlays remain visible regardless of opacity setting.
  - [ ] Edge case: opacity change is instant and does not reload the scene.

- As a retrofit workshop operator, I want to toggle between "before" and "after" views so that I can clearly see what changes the retrofit proposes.
  - [ ] "Before" view shows deviations highlighted on the original vehicle state.
  - [ ] "After" view shows retrofit components installed, deviations resolved.
  - [ ] Toggle is a simple two-state button above the scene.
  - [ ] Edge case: when no components exist, "After" view shows the vehicle without overlays.

- As a retrofit workshop floor staff member, I want to view the digital twin on my mobile device so that I can reference it during installation.
  - [ ] QR code export button generates a scannable QR from the current assessment.
  - [ ] QR code links to a mobile-responsive web viewer with touch controls.
  - [ ] Viewer renders the same twin data (deviations, components, fitment, routes, heat zones).
  - [ ] Edge case: QR generation fails gracefully if twin data is too large.

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
- Enterprise 3D digital twin with battery fitment visualization, measurement tools, heat zone overlays, wiring routes, cutaway controls, before/after comparison, and QR-based mobile viewer.

## What We'd Add With More Time
- Physics-based thermal simulation (heat zones are heuristic in v1).
- Real-time CAD editing within the digital twin scene.
- Multi-user collaboration in the 3D viewer.
- Photorealistic rendering with PBR materials and environment lighting.
- On-device AR overlay (QR-based mobile viewer is the first step).

## Non-Goals
- Passenger car-first launch behavior is out of scope for initial launch wedge, because it materially increases variability and slows validation of the core workshop workflow.
- OEM-first go-to-market workflow is out of scope for this phase, because enterprise procurement/validation flows are not required to prove workshop product value.
- Fleet-first onboarding and operations workflows are out of scope for initial release, because workshop intelligence proof comes first.
- Generic analytics-heavy landing dashboard is out of scope for first run, because it delays trust-building time-to-value.
- Binary validator behavior that blocks non-critical input issues is out of scope, because real workshop environments require tolerant, confidence-aware operation.
- Physics-based thermal simulation is out of scope for the digital twin v1; heat zones are heuristic.
- Real-time CAD editing within the digital twin scene is out of scope.
- Multi-user collaboration in the 3D viewer is out of scope for the initial release.

## Open Questions
- What exact confidence thresholds map to "full confidence," "reduced confidence," "partial assessment," and "unsafe to assess" states? (Needs answer before /spec.)
- What is the minimum required evidence set for a hard safety block vs limited-analysis continuation for each supported vehicle class? (Needs answer before /spec.)
- Which risk labels and severity tiers should be standardized in the first release so operators see consistent language? (Needs answer before /spec.)
- Which compliance output fields are required in the first demo-ready report vs added later in deeper certification workflows? (Can be refined during /spec.)
