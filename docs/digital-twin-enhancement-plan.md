# RetroMind AI — Digital Twin Enhancement Plan

## Guiding Principle
**Add, never replace.** Every new feature sits *alongside* existing ones. The existing 3D scene (procedural vehicle model, deviation overlays, retrofit component markers, hover/click interaction, CAD export) is preserved at every layer. No existing tests break. All new features are gated behind optional data fields that default to `null`/`[]`.

---

## Current Digital Twin (Preserved As-Is)

| Feature | Backend | Frontend | File |
|---------|---------|----------|------|
| Procedural vehicle model | `DigitalTwinDataGenerator.generate()` returns dimensions | `buildRickshawModel()` creates body, cabin, windshield, bed, wheels | `backend/ai/digital_twin/data.py` → `frontend/src/lib/rickshaw-model.ts` |
| Deviation overlays | `_build_deviations_3d()` maps parameters → 3D locations + colors | `buildDeviationOverlays()` creates pulsing transparent boxes | same |
| Retrofit component markers | `_build_retrofit_components()` maps recommendations → component templates | `buildRetrofitComponents()` creates colored boxes + wireframe edges | same |
| Hover tooltips | — | Raycaster hover → emissive glow + floating label | `DigitalTwinSceneContent.tsx` |
| Click selection panel | — | Click → bottom info card with component name/color | `DigitalTwinSceneContent.tsx` |
| CAD export (STEP/STL) | `FreeCADClient` + `cad_export.py` endpoint | Download buttons in AssessmentResult + Reports | `infrastructure/freecad_client.py`, `api/v1/endpoints/cad_export.py` |

---

## Enhancement Items

### 1. Battery Pack Fitment Visualization

**Value**: Answers the #1 retrofit question — "Will the battery fit?"

**Backend changes** (`backend/ai/digital_twin/data.py`):

Add a new method `_build_battery_fitment()` that produces battery fitment data from the assessment result:

```python
def _build_battery_fitment(self, assessment_result: dict) -> dict | None:
    battery_placement = assessment_result.get("battery_placement")
    if not battery_placement:
        return None

    zones = battery_placement.get("zones", [])
    recommended_id = battery_placement.get("recommended_zone")
    recommended = next((z for z in zones if z.get("id") == recommended_id), zones[0] if zones else None)
    if not recommended:
        return None

    return {
        "zone_id": recommended.get("id", "A"),
        "position": {"x": 0.0, "y": -0.25, "z": 0.15},   # from zone constraints
        "size": {"w": 0.6, "h": 0.22, "d": 0.4},          # from battery dimensions
        "clearance": {"front": 15, "rear": 20, "left": 10, "right": 10, "top": 25, "bottom": 30},
        "fitment_status": "tight" if battery_placement.get("confidence", 100) < 60 else "clear",
        "label": "48V LiFePO4 Battery Pack",
    }
```

Inject into `generate()` output:
```python
return {
    ...  # existing fields
    "battery_fitment": self._build_battery_fitment(assessment_result),
}
```

**Frontend changes**:

Add `BatteryFitmentOverlay` component (`frontend/src/lib/battery-fitment.ts`):
- Semi-transparent battery box with fitment status coloring:
  - Green `#10b981` for `"clear"` — full opacity, subtle glow
  - Yellow `#eab308` for `"tight"` — slightly pulsing, caution indicator
  - Red `#ef4444` for `"conflict"` — pulsing more aggressively, warning icon
- Clearance zone bounding box (faint wireframe rectangle around the battery)
- Distance labels on hover (mm values for each clearance direction)
- Toggle via a button in the scene toolbar: "Show Fitment" / "Hide Fitment"

Type addition (`frontend/src/types/assessment.ts`):
```typescript
export interface BatteryFitment {
  zone_id: string;
  position: { x: number; y: number; z: number };
  size: { w: number; h: number; d: number };
  clearance: Record<string, number>;
  fitment_status: "clear" | "tight" | "conflict";
  label: string;
}
```

**Acceptance criteria**:
- Battery pack renders at the correct position with correct dimensions
- Clearance wireframe box is visible on hover
- Fitment status color is consistent with the backend assessment
- Toggle button shows/hides the overlay
- No regression to existing deviation/component rendering

---

### 2. Interactive Measurement Tools

**Value**: Allows retrofit shops to answer spatial questions without physically measuring the vehicle.

**Frontend changes** (purely additive, no backend changes):

Add measurement mode to `DigitalTwinSceneContent.tsx`:

1. **Toolbar** — row of icon buttons above the 3D scene:
   - [Orbit] (default) — standard orbit controls
   - [Measure] — enters measurement mode

2. **Measurement mode** (`frontend/src/lib/measurement-tool.ts`):
   - First click: places a small red sphere (point A), shows tooltip "Click second point"
   - Second click: places a blue sphere (point B)
     - Draws a dashed line between A and B using `THREE.Line` with `LineDashedMaterial`
     - Shows distance label at midpoint: e.g., "425 mm"
     - Distance computed as `pointA.distanceTo(pointB) * 1000` (scene coords are meters → mm)
   - Subsequent clicks: continue adding points; each segment shows its own distance
   - Right-click or toolbar button to clear and exit measurement mode
   - Max 10 point pairs per session; "Clear All Measurements" button

3. **Integration**:
   - Add `measurementMode` state boolean in `DigitalTwinSceneContent`
   - When `measurementMode = true`, disable OrbitControls temporarily (set `controls.enabled = false`)
   - Add `measurementLineRef` and `measurementPointRef` to track Three.js objects
   - Clean up in the effect's return callback

**Types** (`frontend/src/types/assessment.ts`):
```typescript
export interface MeasurementPoint {
  x: number;
  y: number;
  z: number;
}

export interface MeasurementSegment {
  start: MeasurementPoint;
  end: MeasurementPoint;
  distanceMm: number;
}
```

**Acceptance criteria**:
- User can toggle between orbit and measure mode
- Clicks place measurement points with visual markers
- Distance is computed and displayed in mm
- Measurements clear on right-click or button press
- Orbit controls are restored when exiting measure mode
- Existing scene interactions (hover, click-on-component) are unchanged when in orbit mode

---

### 3. Thermal / Heat Zone Overlays

**Value**: Enables safe component placement by visualizing heat sources.

**Backend changes** (`backend/ai/digital_twin/data.py`):

Add a new method `_build_thermal_zones()`:

```python
def _build_thermal_zones(self, assessment_result: dict) -> list[dict]:
    # Heat zones derived from vehicle type defaults + any detected thermal risks
    # In future, could come from actual thermal imaging or simulation
    zones = []

    # Default heat zones per vehicle type
    if geometry_result := assessment_result.get("geometry_result"):
        engine_comp = geometry_result.get("engine_bay_compartment", "rear")
        if engine_comp == "rear":
            zones.append({
                "id": "exhaust_area",
                "label": "Exhaust / Engine Bay",
                "position": {"x": 0.0, "y": -0.1, "z": -0.5},
                "radius": 0.35,
                "severity": "high",
                "temperature_c": 120,
                "source": "oem_default",
            })
        else:
            zones.append({
                "id": "exhaust_area",
                "label": "Exhaust / Engine Bay",
                "position": {"x": 0.0, "y": -0.1, "z": 0.5},
                "radius": 0.35,
                "severity": "high",
                "temperature_c": 120,
                "source": "oem_default",
            })

    # Add zones from deviation data (e.g., damaged heat shielding)
    deviations = (assessment_result.get("deviation_result") or {}).get("deviations", [])
    for d in deviations:
        if "heat" in d.get("notes", "").lower() or "thermal" in d.get("notes", "").lower():
            param = d.get("parameter", "unknown")
            location = _DEVIATION_LOCATIONS.get(param, "chassis_center")
            zones.append({
                "id": f"thermal_deviation_{param}",
                "label": d.get("notes", f"Heat anomaly: {param}"),
                "position": dict(_DEVIATION_3D_POSITIONS.get(location, {"x": 0, "y": 0, "z": 0})),
                "radius": 0.25,
                "severity": "high",
                "temperature_c": 80,
                "source": "deviation_detection",
            })

    return zones
```

Inject into `generate()` output:
```python
return {
    ...  # existing fields
    "thermal_zones": self._build_thermal_zones(assessment_result),
}
```

**Frontend changes**:

Add `buildThermalZones()` (`frontend/src/lib/thermal-zones.ts`):
- For each thermal zone, create a translucent sphere or hemisphere gradient
- Color scale: low (green `#22c55e`) → medium (yellow `#eab308`) → high (red `#ef4444`)
- Use `THREE.SphereGeometry` with radial gradient texture created via Canvas
- Optional: add a temperature label at the center
- Toggle via toolbar button: "Heat Zones" / "Hide Heat Zones"
- Heat zones pulse slowly (different phase from deviation overlays)

**Types** (`frontend/src/types/assessment.ts`):
```typescript
export interface ThermalZone {
  id: string;
  label: string;
  position: { x: number; y: number; z: number };
  radius: number;
  severity: "low" | "medium" | "high";
  temperature_c: number;
  source: string;
}
```

**Acceptance criteria**:
- Default heat zones render for known vehicle types
- Deviation-triggered heat zones appear when notes mention heat/thermal
- Color gradient matches temperature severity
- Toggle button controls visibility
- No overlap with existing deviation overlay rendering

---

### 4. Wiring Route Visualization

**Value**: Gives operators a clear 3D view of proposed HV wiring paths.

**Backend changes** (`backend/ai/digital_twin/data.py`):

Add a new method `_build_wiring_routes()`:

```python
def _build_wiring_routes(self, assessment_result: dict) -> list[dict]:
    wiring = assessment_result.get("wiring_guidance")
    if not wiring:
        return []

    routes = []
    recommended_route = wiring.get("recommended_route") or (wiring.get("routes") or [None])[0]
    if not recommended_route:
        return []

    # Build 3D waypoints from routing description
    # Each route has labeled waypoints from battery → controller → motor
    waypoints_map = {
        "under_seat_forward": [
            {"x": 0.0, "y": -0.1, "z": 0.3},    # battery
            {"x": 0.0, "y": 0.05, "z": 0.2},     # controller
            {"x": 0.0, "y": -0.1, "z": -0.3},    # along frame rail
            {"x": 0.0, "y": -0.2, "z": -0.6},    # motor
        ],
        "underbody_center": [
            {"x": 0.0, "y": -0.1, "z": 0.3},
            {"x": 0.0, "y": -0.3, "z": 0.0},
            {"x": 0.0, "y": -0.3, "z": -0.3},
            {"x": 0.0, "y": -0.2, "z": -0.6},
        ],
    }

    route_id = recommended_route.get("id", "default")
    waypoints = waypoints_map.get(route_id, waypoints_map["under_seat_forward"])

    routes.append({
        "id": route_id,
        "label": recommended_route.get("label", "Primary HV Route"),
        "waypoints": waypoints,
        "color": "#f59e0b",
        "caution_zones": wiring.get("caution_zones", []),
        "confidence": wiring.get("confidence", 0.5),
    })

    return routes
```

Inject into `generate()` output:
```python
return {
    ...  # existing fields
    "wiring_routes": self._build_wiring_routes(assessment_result),
}
```

**Frontend changes**:

Add `buildWiringRoutes()` (`frontend/src/lib/wiring-routes.ts`):
- For each route, draw a 3D tube/spline through waypoints using `THREE.CatmullRomCurve3` and `TubeGeometry`
- Color the tube based on route confidence (high = amber `#f59e0b`, low = dashed/transparent)
- Add small sphere markers at each waypoint
- Caution zones: small red/orange translucent cylinders at waypoint positions
- Toggle via toolbar button: "Wiring Routes" / "Hide Wiring Routes"

**Types** (`frontend/src/types/assessment.ts`):
```typescript
export interface Waypoint3D {
  x: number; y: number; z: number;
}

export interface WiringRoute3D {
  id: string;
  label: string;
  waypoints: Waypoint3D[];
  color: string;
  caution_zones: string[];
  confidence: number;
}
```

**Acceptance criteria**:
- Wiring route renders as a smooth 3D tube through waypoints
- Waypoint markers are visible
- Caution zones are highlighted
- Toggle button controls visibility
- Routes update when battery placement changes

---

### 5. Cutaway / Transparency Controls

**Value**: Reveals internal routing and component placement otherwise hidden behind body panels.

**Frontend changes** (purely additive, no backend changes):

Add a transparency slider/control to `DigitalTwinSceneContent.tsx`:

1. **UI element** — A slider component rendered below the 3D scene or as a floating control:
   ```tsx
   <div className="flex items-center gap-2 px-3 py-2">
     <span className="text-[10px] text-zinc-400">Body Opacity</span>
     <input
       type="range"
       min="10"
       max="100"
       value={bodyOpacity}
       onChange={(e) => setBodyOpacity(Number(e.target.value))}
       className="w-24"
     />
     <span className="text-[10px] font-mono text-zinc-500">{bodyOpacity}%</span>
   </div>
   ```

2. **Implementation**:
   - Store references to body meshes in `rickshaw-model.ts`: return body/cabin/bed meshes separately so their materials can be toggled
   - Add `setBodyOpacity(opacity: number)` function that adjusts `material.opacity` and `material.transparent` on body/cabin/bed meshes
   - When opacity < 100, set `renderOrder = 1` and `depthWrite = false` on body meshes so they render behind transparent objects correctly
   - Deviation overlays and retrofit components are always fully opaque regardless of body opacity

3. **Integration with DigitalTwinSceneContent**:
   - Refactor `buildRickshawModel()` to return a `{ group, bodyMeshes: THREE.Mesh[] }` instead of just `THREE.Group`
   - The existing code that adds the group to the scene remains unchanged
   - New `bodyOpacity` state (default 100) drives the slider
   - `useEffect` updates body mesh material opacity on change

**Acceptance criteria**:
- Slider controls body panel transparency from 10% to 100%
- Internal components (battery, motor, controller) remain fully opaque
- Deviation overlays remain fully opaque
- Wheels/windshield are not affected by the slider
- Scene depth sorting is correct at all opacity levels

---

### 6. Before/After State Toggle

**Value**: Demonstrates the transformation from damaged/modified vehicle to retrofit proposal.

**Frontend changes** (purely additive, no backend changes):

Add a toggle to `DigitalTwinSceneContent.tsx`:

1. **UI** — Two toggle buttons above the scene:
   ```tsx
   <div className="flex gap-1 rounded-lg border p-0.5">
     <button ...>Before</button>
     <button ...>After</button>
   </div>
   ```

2. **"Before" state** (default):
   - Deviation overlays visible and pulsing
   - Retrofit components hidden
   - Vehicle body colored in warm/neutral tones (current behavior)

3. **"After" state**:
   - Deviation overlays hidden (deviations have been "fixed")
   - Retrofit components visible and highlighted
   - Battery fitment overlay visible (if data exists)
   - Wiring routes visible (if data exists)
   - Vehicle body colored in a slightly cooler/cleaner tone (optional subtle color shift)

4. **Implementation**:
   - Add `viewState: "before" | "after"` state
   - `useEffect` toggles visibility of `deviationMeshesRef` and `componentMeshesRef` groups
   - When toggling to "after", auto-show battery fitment and wiring routes
   - When toggling to "before", hide battery fitment and wiring routes
   - Buttons use active/inactive styling

**Acceptance criteria**:
- "Before" shows deviations, hides components
- "After" shows components, hides deviations
- Toggle is smooth (no scene reload)
- Existing interactions work in both states

---

### 7. QR Code for AR View

**Value**: Allows workshop floor staff to view the digital twin on a mobile device.

**Backend changes**:

Add a new endpoint `GET /api/v1/digital-twin/{assessment_id}/qr` in a new file or in `cad_export.py`:

```python
@router.get("/digital-twin/{assessment_id}/qr")
def export_digital_twin_qr(
    assessment_id: str,
    workshop: Workshop = Depends(get_current_workshop_obj),
    db: Session = Depends(get_db),
):
    # 1. Look up job/assessment by ID
    job = db.query(Job).join(Intake).filter(Job.id == assessment_id).first()
    if not job or not job.result:
        raise HTTPException(404, "Assessment not found")

    # 2. Extract digital twin data from job result
    twin_data = job.result.get("digital_twin")
    if not twin_data:
        raise HTTPException(404, "No digital twin data available")

    # 3. Serialize twin data as compact JSON
    twin_json = json.dumps(twin_data, separators=(",", ":"))

    # 4. Compress for QR efficiency (deflate/base64)
    compressed = base64.urlsafe_b64encode(
        gzip.compress(twin_json.encode())
    ).decode()

    # 5. Build URL: webapp that renders Three.js from URL param
    #    Frontend route: /view-twin?d=<compressed>
    qr_content = f"{settings.frontend_url}/view-twin?d={compressed}"

    # 6. Generate QR code as PNG
    import qrcode
    from io import BytesIO
    img = qrcode.make(qr_content, box_size=10)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return Response(content=buf.getvalue(), media_type="image/png")
```

Dependency: add `qrcode` to `backend/requirements.txt`.

**Frontend changes**:

1. **QR export button** in AssessmentResult + Reports:
   ```tsx
   <button onClick={handleQrExport}>
     <QrCodeIcon /> Mobile View
   </button>
   ```

2. **New route** `frontend/src/app/view-twin/page.tsx`:
   - Reads `d` query param
   - Decompresses (`gzip` → `base64` → JSON parse)
   - Renders the same `DigitalTwinScene` component with the extracted data
   - Mobile-responsive layout (full-screen, touch-friendly orbit controls)
   - Instructions overlay: "Pinch to zoom, drag to orbit"
   - Auto-rotate option for demonstration

3. **Touch controls**: Three.js `OrbitControls` already supports touch events; add `enableRotate = true`, `enablePan = false` for mobile

**Types**: No new types needed — reuses existing `DigitalTwinData`.

**Acceptance criteria**:
- QR code exports as PNG download
- Scannable QR navigates to the web viewer
- Web viewer renders the same digital twin data
- Touch controls work on mobile
- Compact URL fits within QR capacity (< 3KB compressed data)

---

## Implementation Order

| Priority | Item | Effort | Dependencies | Enterprise Value |
|:--------:|------|:------:|-------------|:----------------:|
| 1 | Battery Pack Fitment Visualization | Medium | None | Highest (#1 retrofit question) |
| 2 | Interactive Measurement Tools | Medium | None | High (answers spatial questions) |
| 3 | Wiring Route Visualization | Small | Item 1 (reuses scene) | High (safety + install speed) |
| 4 | Cutaway / Transparency Controls | Small | None | Medium (reveals hidden components) |
| 5 | Thermal / Heat Zone Overlays | Small | None | Medium (safety planning) |
| 6 | Before/After State Toggle | Small | Items 1-3 (needs components) | Medium (demonstrates value) |
| 7 | QR Code for AR View | Medium | None | Medium (on-floor reference) |

**Recommended sprint ordering**:
- **Sprint 1**: Battery fitment + Measurement tools
- **Sprint 2**: Wiring routes + Cutaway controls
- **Sprint 3**: Thermal zones + Before/After toggle
- **Sprint 4**: QR code + mobile viewer

---

## Non-Goals for This Phase
- Physics-based thermal simulation (heat zone data is heuristic)
- Real-time CAD editing (export is static STEP/STL only)
- Multi-user collaboration in the 3D scene
- Photorealistic rendering (PBR materials are sufficient)

---

## Backward Compatibility Guarantee
- All existing `DigitalTwinData` fields remain required
- New fields (`battery_fitment`, `thermal_zones`, `wiring_routes`) are `Optional` and default to `null`/`[]`
- Existing `DigitalTwinSceneContent` renders without errors when new fields are absent
- Existing tests (`test_digital_twin.py`) continue to pass unchanged
- The `DigitalTwinDataGenerator.generate()` output grows additively
