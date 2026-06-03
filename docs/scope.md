# RetroMind AI

## Idea
A self-learning EV retrofit intelligence network that helps retrofit workshops convert imperfect real-world ICE vehicles into safer, more consistent EVs through deviation-aware AI engineering, optimization, and adaptive design automation.

## Who It's For
Primary launch user: independent EV retrofit workshops and small workshop networks in India (Tier 1 and Tier 2 retrofit ecosystems).

Core unmet need:
- They currently depend on tribal engineering knowledge and manual workflows that are slow, inconsistent, and hard to scale.
- They face real-world vehicle imperfections (undocumented repairs, deformation, welded modifications, asymmetry) that static retrofit tools do not handle well.
- They need practical, affordable, workshop-friendly intelligence that reduces engineering effort while improving safety and standardization.

## Inspiration & References
- Autodesk Generative Design: constraint-driven design exploration and multi-option engineering optimization.
  - https://www.autodesk.com/solutions/generative-design
- FreeCAD: open, scriptable parametric CAD automation aligned with CAD-ready retrofit outputs.
  - https://www.freecad.org
- Neo4j knowledge graph patterns: relationship-first modeling to support Retrofit DNA and ecosystem learning.
  - https://neo4j.com/use-cases/knowledge-graph/

Design and product energy:
- Technically expressive, explainable engineering visuals over abstract aesthetics.
- "Show me how it works" experience: system maps, risk overlays, digital twin-like behavior views, and engineering dashboard clarity.

## Goals
- Build a production-grade direction, not a throwaway prototype, while still executing a credible hackathon delivery slice.
- Demonstrate that retrofit intelligence can be deviation-aware for imperfect vehicles, not only factory-standard assumptions.
- Prove self-learning value through a Retrofit DNA / knowledge graph narrative that compounds over time.
- Show practical workshop impact: reduced engineering effort, faster turnaround, safer retrofit decisions.
- Create a foundation that expands from workshop wedge to broader multi-vehicle and enterprise retrofit ecosystems.

## What "Done" Looks Like
For this hackathon phase, done means a convincing, end-to-end launch wedge demonstration with production-grade architecture intent:
- Target scenario: ICE auto-rickshaw (three-wheeler) conversion context in India.
- Input and analysis: vehicle images/scans processed for structural/deviation cues.
- Decision layer: feasibility and risk scoring with clear engineering confidence outputs.
- Core intelligence moment: deviation-aware battery placement recommendations under constraints.
- Engineering outputs: adaptive wiring route logic and CAD-ready output direction (parametric workflow path).
- Visualization layer: lightweight retrofit twin style view for stress/thermal/safety interpretation.
- Learning layer: Retrofit DNA concept represented in a knowledge graph to show how prior outcomes improve future recommendations.
- Demo story: not just model output, but a coherent engineering-assistant workflow a workshop can trust.

## What's Explicitly Cut
- Passenger cars as the first anchor: cut for initial launch wedge due to high structural/electronic complexity and reduced execution speed.
- OEM-first go-to-market: cut for initial phase due to long validation/procurement timelines.
- Fleet-first go-to-market: cut initially; positioned as phase-two after workshop data flywheel and reliability proof.
- Generic broad multi-vehicle-first execution: cut for launch wedge (while retained as long-term platform trajectory).

## Loose Implementation Notes
- Architecture direction:
  - Frontend: Next.js + TailwindCSS + technical visualization patterns (Three.js where useful).
  - AI/backend: FastAPI + PyTorch/OpenCV/ONNX runtime components.
  - Optimization: practical multi-objective stack (e.g., SciPy/Optuna, optionally RL where justified).
  - CAD automation path: FreeCAD/OpenSCAD scripting-ready interfaces.
  - Data/intelligence: Neo4j (Retrofit DNA graph) + operational persistence (PostgreSQL/MongoDB as needed).
- Product framing for judges and stakeholders:
  - Start narrow where pain and repeatability are highest (three-wheeler workshops in India).
  - Emphasize compounding intelligence: every retrofit improves the next retrofit.
  - Anchor differentiation in deviation-aware engineering decisions, not generic AI labels.
- Scope principle:
  - Preserve the long-term full-production vision.
  - Sequence delivery through an executable launch wedge that proves safety, speed, and intelligence.
