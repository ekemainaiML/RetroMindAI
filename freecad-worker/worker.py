"""FreeCAD worker — builds 3D models from assessment data and exports STEP/STL.

Runs in a separate container with freecad-python3 installed.
Receives assessment results via REST and returns binary file data.
"""

import logging
import os
import sys
import tempfile
import uuid

for _p in ("/usr/lib/freecad/lib", "/usr/lib/freecad-python3/lib", "/usr/lib/python3/dist-packages"):
    if os.path.isdir(_p):
        sys.path.insert(0, _p)
        break
from fastapi import FastAPI, Response
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(title="FreeCAD Worker")


class ExportRequest(BaseModel):
    assessment: dict
    format: str = "step"


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")


@app.post("/export")
def export_step(req: ExportRequest):
    try:
        import FreeCAD
        import Part
        import Mesh
    except ImportError:
        logger.error("FreeCAD Python libraries not available")
        return Response(
            content='{"error":"FreeCAD not available"}',
            status_code=503,
            media_type="application/json",
        )

    doc = FreeCAD.newDocument("RetroMindExport")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{req.format}")
    try:
        body = _build_model(doc, req.assessment)
        tmp.close()

        if req.format == "stl":
            shape = body.Shape if hasattr(body, "Shape") else body
            import MeshPart
            mesh = MeshPart.meshFromShape(shape, LinearDeflection=0.5, AngularDeflection=0.5)
            mesh.write(tmp.name)
            media_type = "application/sla"
        else:
            Part.export([body], tmp.name)
            media_type = "application/step"

        with open(tmp.name, "rb") as f:
            content = f.read()

        filename = f"{uuid.uuid4()}.{req.format}"
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception:
        logger.exception("FreeCAD model generation failed")
        return Response(
            content='{"error":"Model generation failed"}',
            status_code=500,
            media_type="application/json",
        )
    finally:
        FreeCAD.closeDocument("RetroMindExport")
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


def _build_model(doc, assessment: dict):
    vehicle_type = (
        assessment.get("vehicle_classification", {}) or {}
    ).get("type", "unknown")
    geometry = assessment.get("geometry_result", {}) or {}

    length = _get_measurement(geometry, "length", 3000)
    width = _get_measurement(geometry, "width", 1500)
    height = _get_measurement(geometry, "height", 1200)
    wheelbase = _get_measurement(geometry, "wheelbase", 2000)

    body = doc.addObject("Part::Box", "Body")
    body.Length = length
    body.Width = width
    body.Height = height
    body.recompute()

    cabin = doc.addObject("Part::Box", "Cabin")
    cabin.Length = length * 0.4
    cabin.Width = width * 0.8
    cabin.Height = height * 0.2
    cabin.Placement.Base = (length * 0.05, width * 0.1, height * 0.5)
    cabin.recompute()

    fusion = doc.addObject("Part::MultiFuse", "Chassis")
    fusion.Shapes = [body, cabin]
    fusion.recompute()

    return fusion


def _get_measurement(geometry: dict, key: str, default: float) -> float:
    measurements = geometry.get("measurements", {}) or {}
    val = measurements.get(key, {}) or {}
    return float(val.get("mm", default))
