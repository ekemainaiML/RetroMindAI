# RetroMind AI — EV Retrofit Intelligence for Imperfect Vehicles

## Subtitle
Making Every Vehicle Retrofit-Ready: AI-Powered Assessment for the 3-Wheeler Revolution

## Elevator Pitch
RetroMind AI enables independent workshops to assess any vehicle for EV conversion in under 60 seconds. Upload three photos, get a structured feasibility report with confidence scoring, risk analysis, and retrofit recommendations. Built for the real world — blurry photos, swapped sides, structural damage, and all.

## Inspiration
India has 8 million+ auto-rickshaws, most with ICE engines nearing end of life. Independent retrofit workshops are the backbone of this conversion ecosystem — but they operate on intuition, not data. Every vehicle is different: 15-year-old frames, backyard modifications, mixed spare parts. Workshop owners told us: "I can tell if a vehicle is fit for conversion by looking at it, but I can't prove it to the customer or the regulator."

RetroMind AI digitizes that expertise. Three photos → structured, auditable feasibility report.

## What it does
- **Upload**: 3 photos (left profile, right profile, rear view) via mobile-friendly web interface
- **Analyze**: AI pipeline classifies vehicle type, extracts geometry, detects structural deviations, and computes retrofit feasibility — all in under 60 seconds
- **Report**: Confidence-scored feasibility assessment with risk register, deviation map, cost estimates, and retrofit recommendations
- **Digital Twin**: Interactive 3D visualization showing deviation hotspots and recommended component placements
- **Learn**: Every assessment feeds a knowledge graph (Neo4j) for cross-vehicle pattern matching — "Retrofit DNA"

## How we built it
### Architecture
- **Frontend**: Next.js + Tailwind CSS + Three.js (Vercel-deployed)
- **Backend**: FastAPI + SQLAlchemy + RQ async worker (Railway-deployed)
- **Storage**: PostgreSQL (state), Redis (job queue), Neo4j (knowledge graph)
- **AI**: ONNX Runtime for vehicle classification, OpenCV for geometry and deviation detection

### Pipeline (6 stages, async with per-stage timeout isolation)
1. Classification — identifies vehicle type with confidence + alternatives
2. Geometry extraction — structural coverage, symmetry analysis, frame estimation
3. Deviation detection — measures deviations from factory specs, flags critical delamination
4. Confidence scoring — weighted multi-factor engine with safety overrides
5. Recommendations — rules-based retrofit plan with cost estimates and dependency sequencing
6. Digital twin — generates 3D scene metadata for the visualization layer

### Key design decisions
- REST-only async transport (no WebSockets/SSE — polling via GET /api/v1/jobs/{id})
- Mock-first AI development: all AI stages fall back gracefully when models are unavailable
- Degradation management: Tier 0-3 infrastructure model ensuring no single failure crashes the system
- Multi-tenant auth-ready boundaries from day one (though v1 is single-tenant demo)

## Challenges we ran into
- **Deterministic deviation detection from 2D photos**: Without LiDAR or structured light, absolute measurement requires intelligent heuristics. We anchor pixel measurements to known reference dimensions and measure proportional deltas rather than absolute values.
- **Image quality variance**: Workshop photos vary wildly — different angles, lighting, occlusion. We built multi-stage validation (blur detection, swap detection, occlusion checks) before the AI pipeline.
- **ONNX compatibility**: Cross-version ONNX IR compatibility required careful opset selection. Fixed by generating test models with IR version 9/opset 11.
- **Docker CI reliability**: Python+OpenCV Docker builds are slow. Optimized with multi-stage builds and pip `--no-cache-dir`.

## Accomplishments we're proud of
- Full async job pipeline with per-stage timeouts, auto-retry, and partial result salvage
- Confidence engine that weights 6 factors (quality, geometry, visibility, completeness, classification, deviation certainty)
- 3D digital twin rendered from structured metadata — no heavy 3D models needed
- 138 passing tests across the entire system
- Docker Compose one-command startup for the full stack (Postgres + Redis + Neo4j + API + Worker)

## What we learned
- **Confidence is harder than correctness**: Communicating "I'm 78% sure this is feasible" is harder than saying "it's feasible." The multi-factor confidence engine evolved from a week of thinking about what makes workshop decisions trustworthy.
- **Real-world AI needs graceful degradation**: Models fail, infrastructure flakes, uploads are messy. The degradation manager (Tier 0-3) was one of the most important architectural decisions.
- **Procedural 3D is surprisingly effective**: We don't need photorealistic digital twins. Colored boxes with deviation overlays communicate more than a perfect mesh with no annotations.

## What's next
- **Trained vehicle classifier**: Replace the ONNX test model with a real trained model (dataset of 10K+ Indian 3-wheeler photos)
- **Mobile app**: Native camera integration with real-time blur feedback for better uploads
- **Regulatory compliance module**: Generate RTO-ready conversion certificates from assessment data
- **Workshop CRM**: Track retrofit projects through completion with parts ordering integration
- **Fleet mode**: Batch assessment API for fleet operators evaluating 50+ vehicles
