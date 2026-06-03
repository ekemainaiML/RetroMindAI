import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.v1.models.intake import JobResponse
from core.auth import get_current_workshop
from core.database import get_db
from core.models import Intake, Job
from optimization.battery import compute_battery_zones
from optimization.wiring import compute_routing
from seed_data.demo_vehicles import DEMO_VEHICLES

router = APIRouter()


class DemoVehicleInfo(BaseModel):
    index: int
    name: str
    vehicle_type: str
    description: str


class DemoListResponse(BaseModel):
    vehicles: list[DemoVehicleInfo]


class DemoLaunchResponse(BaseModel):
    job_id: str
    status: str
    vehicle_name: str
    assessment_state: str


@router.get("/demo/list", response_model=DemoListResponse)
async def list_demo_vehicles():
    vehicles = [
        DemoVehicleInfo(
            index=i,
            name=v["name"],
            vehicle_type=v["vehicle_type"],
            description=v["description"],
        )
        for i, v in enumerate(DEMO_VEHICLES)
    ]
    return DemoListResponse(vehicles=vehicles)


@router.post("/demo/{vehicle_index}", response_model=DemoLaunchResponse)
async def load_demo_vehicle(
    vehicle_index: int,
    db: Session = Depends(get_db),
    workshop_id: str = Depends(get_current_workshop),
):
    if vehicle_index < 0 or vehicle_index >= len(DEMO_VEHICLES):
        raise HTTPException(
            status_code=404,
            detail=f"Demo vehicle not found at index {vehicle_index}. Available: 0-{len(DEMO_VEHICLES) - 1}",
        )

    vehicle = DEMO_VEHICLES[vehicle_index]
    vdata = vehicle["assessment"]

    intake_id = uuid.uuid4()
    job_id = uuid.uuid4()

    intake = Intake(
        id=intake_id,
        workshop_id=uuid.UUID(workshop_id),
        view_slots={
            "left_side_profile": f"demo://{vehicle['name']}/left_side",
            "right_side_profile": f"demo://{vehicle['name']}/right_side",
            "rear_view": f"demo://{vehicle['name']}/rear",
        },
        attempts={},
        quality_scores={
            "left_side_profile": 85.0,
            "right_side_profile": 82.0,
            "rear_view": 90.0,
        },
        low_quality_views=[],
        swap_detected=False,
        status="ready",
    )
    db.add(intake)

    result = dict(vdata)
    result["recommendations"] = vehicle.get("recommendations", [])
    result["risks"] = vehicle.get("risks", [])
    result["risk_register"] = vehicle.get("risks", [])
    result["deviations"] = vehicle.get("deviations", [])
    result["digital_twin"] = vehicle.get("digital_twin")
    result["similar_retrofits"] = [
        {
            "vehicle_id": "demo-ref-001",
            "type": "three_wheeler",
            "matching_deviations": 2,
            "confidence": 0.78,
        },
    ]
    result["estimated_total_cost_inr"] = vehicle.get("estimated_total_cost_inr", 0)
    result["tooling_required"] = vehicle.get("tooling_required", [])
    result["skill_level_required"] = vehicle.get("skill_level_required", "intermediate")
    result["estimated_days"] = vehicle.get("estimated_days", 0)

    try:
        vtype = vdata.get("vehicle_classification", {}).get("type", "three_wheeler")
        deviation_result = vehicle.get("deviation_result")
        geometry_result = vehicle.get("geometry_result")
        bp = compute_battery_zones(vtype, deviation_result, geometry_result)
        result["battery_placement"] = bp
        wg = compute_routing(vtype, bp.get("recommended_zone"), deviation_result, geometry_result)
        result["wiring_guidance"] = wg
    except Exception:
        pass

    job = Job(
        id=job_id,
        intake_id=intake_id,
        status="completed",
        current_stage=None,
        progress_pct=100,
        completed_stages=[
            "upload_validation",
            "image_quality_check",
            "vehicle_classification",
            "geometry_extraction",
            "deviation_detection",
            "feasibility_scoring",
            "risk_analysis",
            "battery_optimization",
            "wiring_generation",
            "digital_twin",
            "finalizing",
        ],
        missing_stages=[],
        result=result,
    )
    db.add(job)
    db.commit()

    return DemoLaunchResponse(
        job_id=str(job_id),
        status="completed",
        vehicle_name=vehicle["name"],
        assessment_state=result["assessment_state"],
    )
