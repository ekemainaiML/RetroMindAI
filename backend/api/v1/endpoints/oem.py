import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from api.v1.models.oem import (
    ManufacturerCreate,
    ManufacturerResponse,
    ManufacturerUpdate,
    MountingPointCreate,
    MountingPointResponse,
    MountingPointUpdate,
    OEMLookupResponse,
    RoutingPathCreate,
    RoutingPathResponse,
    RoutingPathUpdate,
    SpecificationCreate,
    SpecificationResponse,
    SpecificationUpdate,
    VehicleModelCreate,
    VehicleModelResponse,
    VehicleModelSearchResult,
    VehicleModelUpdate,
)
from core.auth import get_current_workshop, get_optional_workshop
from core.database import get_db
from core.models import (
    OEMManufacturer,
    OEMMountingPoint,
    OEMRoutingPath,
    OEMSpecification,
    OEMVehicleModel,
)

router = APIRouter()


def _manu_to_response(m: OEMManufacturer, model_count: int = 0) -> ManufacturerResponse:
    return ManufacturerResponse(
        id=str(m.id),
        name=m.name,
        country=m.country,
        founded_year=m.founded_year,
        is_active=m.is_active,
        model_count=model_count,
        created_at=m.created_at.isoformat(),
    )


def _model_to_response(
    vm: OEMVehicleModel,
    manufacturer_name: str = "",
    spec_count: int = 0,
    mounting_point_count: int = 0,
    routing_path_count: int = 0,
) -> VehicleModelResponse:
    return VehicleModelResponse(
        id=str(vm.id),
        manufacturer_id=str(vm.manufacturer_id),
        manufacturer_name=manufacturer_name,
        model_name=vm.model_name,
        generation=vm.generation,
        vehicle_type=vm.vehicle_type,
        year_start=vm.year_start,
        year_end=vm.year_end,
        image_url=vm.image_url,
        is_active=vm.is_active,
        spec_count=spec_count,
        mounting_point_count=mounting_point_count,
        routing_path_count=routing_path_count,
        created_at=vm.created_at.isoformat(),
    )


def _spec_to_response(s: OEMSpecification) -> SpecificationResponse:
    return SpecificationResponse(
        id=str(s.id),
        model_id=str(s.model_id),
        wheelbase_mm=s.wheelbase_mm,
        overall_length_mm=s.overall_length_mm,
        overall_width_mm=s.overall_width_mm,
        overall_height_mm=s.overall_height_mm,
        ground_clearance_mm=s.ground_clearance_mm,
        cargo_length_mm=s.cargo_length_mm,
        cargo_width_mm=s.cargo_width_mm,
        kerb_weight_kg=s.kerb_weight_kg,
        gross_weight_kg=s.gross_weight_kg,
        payload_kg=s.payload_kg,
        seating_capacity=s.seating_capacity,
        engine_cc=s.engine_cc,
        fuel_type=s.fuel_type,
        notes=s.notes,
        created_at=s.created_at.isoformat(),
    )


def _mount_to_response(mp: OEMMountingPoint) -> MountingPointResponse:
    return MountingPointResponse(
        id=str(mp.id),
        model_id=str(mp.model_id),
        point_name=mp.point_name,
        point_type=mp.point_type,
        position_x_mm=mp.position_x_mm,
        position_y_mm=mp.position_y_mm,
        position_z_mm=mp.position_z_mm,
        bolt_pattern=mp.bolt_pattern,
        torque_spec_nm=mp.torque_spec_nm,
        notes=mp.notes,
        created_at=mp.created_at.isoformat(),
    )


def _routing_to_response(rp: OEMRoutingPath) -> RoutingPathResponse:
    return RoutingPathResponse(
        id=str(rp.id),
        model_id=str(rp.model_id),
        path_name=rp.path_name,
        path_type=rp.path_type,
        start_point=rp.start_point,
        end_point=rp.end_point,
        length_estimate_mm=rp.length_estimate_mm,
        constraints=rp.constraints,
        notes=rp.notes,
        created_at=rp.created_at.isoformat(),
    )


# ── Manufacturers ──────────────────────────────────────────────────────


@router.get("/oem/manufacturers", response_model=list[ManufacturerResponse])
def list_manufacturers(
    workshop_id: str | None = Depends(get_optional_workshop),
    db: Session = Depends(get_db),
    search: str | None = Query(None),
    is_active: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = db.query(OEMManufacturer)
    if search:
        query = query.filter(OEMManufacturer.name.ilike(f"%{search}%"))
    if is_active is not None:
        query = query.filter(OEMManufacturer.is_active.is_(is_active))
    manufacturers = query.order_by(OEMManufacturer.name).offset(offset).limit(limit).all()
    model_counts = {
        str(row[0]): row[1]
        for row in db.query(OEMVehicleModel.manufacturer_id, func.count(OEMVehicleModel.id))
        .group_by(OEMVehicleModel.manufacturer_id)
        .all()
    }
    return [_manu_to_response(m, model_counts.get(str(m.id), 0)) for m in manufacturers]


@router.get("/oem/manufacturers/{manufacturer_id}", response_model=ManufacturerResponse)
def get_manufacturer(
    manufacturer_id: str,
    workshop_id: str | None = Depends(get_optional_workshop),
    db: Session = Depends(get_db),
):
    m = db.query(OEMManufacturer).filter(OEMManufacturer.id == uuid.UUID(manufacturer_id)).first()
    if not m:
        raise HTTPException(status_code=404, detail="Manufacturer not found")
    model_count = db.query(OEMVehicleModel).filter(
        OEMVehicleModel.manufacturer_id == m.id
    ).count()
    return _manu_to_response(m, model_count)


@router.post("/oem/manufacturers", response_model=ManufacturerResponse, status_code=201)
def create_manufacturer(
    body: ManufacturerCreate,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    existing = db.query(OEMManufacturer).filter(OEMManufacturer.name == body.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Manufacturer already exists")
    m = OEMManufacturer(
        name=body.name,
        country=body.country,
        founded_year=body.founded_year,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _manu_to_response(m)


@router.put("/oem/manufacturers/{manufacturer_id}", response_model=ManufacturerResponse)
def update_manufacturer(
    manufacturer_id: str,
    body: ManufacturerUpdate,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    m = db.query(OEMManufacturer).filter(OEMManufacturer.id == uuid.UUID(manufacturer_id)).first()
    if not m:
        raise HTTPException(status_code=404, detail="Manufacturer not found")
    if body.name is not None:
        m.name = body.name
    if body.country is not None:
        m.country = body.country
    if body.founded_year is not None:
        m.founded_year = body.founded_year
    if body.is_active is not None:
        m.is_active = body.is_active
    db.commit()
    db.refresh(m)
    model_count = db.query(OEMVehicleModel).filter(
        OEMVehicleModel.manufacturer_id == m.id
    ).count()
    return _manu_to_response(m, model_count)


@router.delete("/oem/manufacturers/{manufacturer_id}", status_code=204)
def delete_manufacturer(
    manufacturer_id: str,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    m = db.query(OEMManufacturer).filter(OEMManufacturer.id == uuid.UUID(manufacturer_id)).first()
    if not m:
        raise HTTPException(status_code=404, detail="Manufacturer not found")
    db.delete(m)
    db.commit()


# ── Vehicle Models ─────────────────────────────────────────────────────


@router.get("/oem/models", response_model=list[VehicleModelResponse])
def list_vehicle_models(
    workshop_id: str | None = Depends(get_optional_workshop),
    db: Session = Depends(get_db),
    manufacturer_id: str | None = Query(None),
    vehicle_type: str | None = Query(None),
    search: str | None = Query(None),
    is_active: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = db.query(OEMVehicleModel)
    if manufacturer_id:
        query = query.filter(OEMVehicleModel.manufacturer_id == uuid.UUID(manufacturer_id))
    if vehicle_type:
        query = query.filter(OEMVehicleModel.vehicle_type == vehicle_type)
    if search:
        query = query.filter(OEMVehicleModel.model_name.ilike(f"%{search}%"))
    if is_active is not None:
        query = query.filter(OEMVehicleModel.is_active.is_(is_active))
    query = query.options(joinedload(OEMVehicleModel.manufacturer))
    models = query.order_by(OEMVehicleModel.model_name).offset(offset).limit(limit).all()
    # compute counts per model
    vm_ids = [vm.id for vm in models]
    spec_counts_raw = {}
    mount_counts_raw = {}
    route_counts_raw = {}
    if vm_ids:
        for row in db.query(OEMSpecification.model_id, func.count(OEMSpecification.id)).filter(
            OEMSpecification.model_id.in_(vm_ids)
        ).group_by(OEMSpecification.model_id).all():
            spec_counts_raw[str(row[0])] = row[1]
        for row in db.query(OEMMountingPoint.model_id, func.count(OEMMountingPoint.id)).filter(
            OEMMountingPoint.model_id.in_(vm_ids)
        ).group_by(OEMMountingPoint.model_id).all():
            mount_counts_raw[str(row[0])] = row[1]
        for row in db.query(OEMRoutingPath.model_id, func.count(OEMRoutingPath.id)).filter(
            OEMRoutingPath.model_id.in_(vm_ids)
        ).group_by(OEMRoutingPath.model_id).all():
            route_counts_raw[str(row[0])] = row[1]
    return [
        _model_to_response(
            vm,
            manufacturer_name=vm.manufacturer.name if vm.manufacturer else "",
            spec_count=spec_counts_raw.get(str(vm.id), 0),
            mounting_point_count=mount_counts_raw.get(str(vm.id), 0),
            routing_path_count=route_counts_raw.get(str(vm.id), 0),
        )
        for vm in models
    ]


@router.get("/oem/models/{model_id}", response_model=VehicleModelResponse)
def get_vehicle_model(
    model_id: str,
    workshop_id: str | None = Depends(get_optional_workshop),
    db: Session = Depends(get_db),
):
    vm = (
        db.query(OEMVehicleModel)
        .options(joinedload(OEMVehicleModel.manufacturer))
        .filter(OEMVehicleModel.id == uuid.UUID(model_id))
        .first()
    )
    if not vm:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    spec_count = db.query(OEMSpecification).filter(OEMSpecification.model_id == vm.id).count()
    mount_count = db.query(OEMMountingPoint).filter(OEMMountingPoint.model_id == vm.id).count()
    route_count = db.query(OEMRoutingPath).filter(OEMRoutingPath.model_id == vm.id).count()
    return _model_to_response(
        vm,
        manufacturer_name=vm.manufacturer.name if vm.manufacturer else "",
        spec_count=spec_count,
        mounting_point_count=mount_count,
        routing_path_count=route_count,
    )


@router.post("/oem/models", response_model=VehicleModelResponse, status_code=201)
def create_vehicle_model(
    body: VehicleModelCreate,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    manu = db.query(OEMManufacturer).filter(
        OEMManufacturer.id == uuid.UUID(body.manufacturer_id)
    ).first()
    if not manu:
        raise HTTPException(status_code=404, detail="Manufacturer not found")
    vm = OEMVehicleModel(
        manufacturer_id=uuid.UUID(body.manufacturer_id),
        model_name=body.model_name,
        generation=body.generation,
        vehicle_type=body.vehicle_type,
        year_start=body.year_start,
        year_end=body.year_end,
        image_url=body.image_url,
    )
    db.add(vm)
    db.commit()
    db.refresh(vm)
    return _model_to_response(vm, manufacturer_name=manu.name)


@router.put("/oem/models/{model_id}", response_model=VehicleModelResponse)
def update_vehicle_model(
    model_id: str,
    body: VehicleModelUpdate,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    vm = (
        db.query(OEMVehicleModel)
        .options(joinedload(OEMVehicleModel.manufacturer))
        .filter(OEMVehicleModel.id == uuid.UUID(model_id))
        .first()
    )
    if not vm:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    if body.model_name is not None:
        vm.model_name = body.model_name
    if body.generation is not None:
        vm.generation = body.generation
    if body.vehicle_type is not None:
        vm.vehicle_type = body.vehicle_type
    if body.year_start is not None:
        vm.year_start = body.year_start
    if body.year_end is not None:
        vm.year_end = body.year_end
    if body.image_url is not None:
        vm.image_url = body.image_url
    if body.is_active is not None:
        vm.is_active = body.is_active
    db.commit()
    db.refresh(vm)
    return _model_to_response(vm, manufacturer_name=vm.manufacturer.name if vm.manufacturer else "")


@router.delete("/oem/models/{model_id}", status_code=204)
def delete_vehicle_model(
    model_id: str,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    vm = db.query(OEMVehicleModel).filter(OEMVehicleModel.id == uuid.UUID(model_id)).first()
    if not vm:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    db.delete(vm)
    db.commit()


# ── Specifications ─────────────────────────────────────────────────────


@router.get("/oem/models/{model_id}/specifications", response_model=list[SpecificationResponse])
def list_specifications(
    model_id: str,
    workshop_id: str | None = Depends(get_optional_workshop),
    db: Session = Depends(get_db),
):
    vm = db.query(OEMVehicleModel).filter(OEMVehicleModel.id == uuid.UUID(model_id)).first()
    if not vm:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    specs = db.query(OEMSpecification).filter(OEMSpecification.model_id == vm.id).all()
    return [_spec_to_response(s) for s in specs]


@router.post(
    "/oem/models/{model_id}/specifications",
    response_model=SpecificationResponse,
    status_code=201,
)
def create_specification(
    model_id: str,
    body: SpecificationCreate,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    vm = db.query(OEMVehicleModel).filter(OEMVehicleModel.id == uuid.UUID(model_id)).first()
    if not vm:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    spec = OEMSpecification(
        model_id=vm.id,
        wheelbase_mm=body.wheelbase_mm,
        overall_length_mm=body.overall_length_mm,
        overall_width_mm=body.overall_width_mm,
        overall_height_mm=body.overall_height_mm,
        ground_clearance_mm=body.ground_clearance_mm,
        cargo_length_mm=body.cargo_length_mm,
        cargo_width_mm=body.cargo_width_mm,
        kerb_weight_kg=body.kerb_weight_kg,
        gross_weight_kg=body.gross_weight_kg,
        payload_kg=body.payload_kg,
        seating_capacity=body.seating_capacity,
        engine_cc=body.engine_cc,
        fuel_type=body.fuel_type,
        notes=body.notes,
    )
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return _spec_to_response(spec)


@router.put(
    "/oem/specifications/{spec_id}",
    response_model=SpecificationResponse,
)
def update_specification(
    spec_id: str,
    body: SpecificationUpdate,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    spec = db.query(OEMSpecification).filter(OEMSpecification.id == uuid.UUID(spec_id)).first()
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")
    for field in (
        "wheelbase_mm", "overall_length_mm", "overall_width_mm", "overall_height_mm",
        "ground_clearance_mm", "cargo_length_mm", "cargo_width_mm", "kerb_weight_kg",
        "gross_weight_kg", "payload_kg", "seating_capacity", "engine_cc", "fuel_type", "notes",
    ):
        val = getattr(body, field, None)
        if val is not None:
            setattr(spec, field, val)
    db.commit()
    db.refresh(spec)
    return _spec_to_response(spec)


@router.delete("/oem/specifications/{spec_id}", status_code=204)
def delete_specification(
    spec_id: str,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    spec = db.query(OEMSpecification).filter(OEMSpecification.id == uuid.UUID(spec_id)).first()
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")
    db.delete(spec)
    db.commit()


# ── Mounting Points ────────────────────────────────────────────────────


@router.get(
    "/oem/models/{model_id}/mounting-points",
    response_model=list[MountingPointResponse],
)
def list_mounting_points(
    model_id: str,
    workshop_id: str | None = Depends(get_optional_workshop),
    db: Session = Depends(get_db),
):
    vm = db.query(OEMVehicleModel).filter(OEMVehicleModel.id == uuid.UUID(model_id)).first()
    if not vm:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    points = db.query(OEMMountingPoint).filter(OEMMountingPoint.model_id == vm.id).all()
    return [_mount_to_response(p) for p in points]


@router.post(
    "/oem/models/{model_id}/mounting-points",
    response_model=MountingPointResponse,
    status_code=201,
)
def create_mounting_point(
    model_id: str,
    body: MountingPointCreate,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    vm = db.query(OEMVehicleModel).filter(OEMVehicleModel.id == uuid.UUID(model_id)).first()
    if not vm:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    mp = OEMMountingPoint(
        model_id=vm.id,
        point_name=body.point_name,
        point_type=body.point_type,
        position_x_mm=body.position_x_mm,
        position_y_mm=body.position_y_mm,
        position_z_mm=body.position_z_mm,
        bolt_pattern=body.bolt_pattern,
        torque_spec_nm=body.torque_spec_nm,
        notes=body.notes,
    )
    db.add(mp)
    db.commit()
    db.refresh(mp)
    return _mount_to_response(mp)


@router.put(
    "/oem/mounting-points/{point_id}",
    response_model=MountingPointResponse,
)
def update_mounting_point(
    point_id: str,
    body: MountingPointUpdate,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    mp = db.query(OEMMountingPoint).filter(OEMMountingPoint.id == uuid.UUID(point_id)).first()
    if not mp:
        raise HTTPException(status_code=404, detail="Mounting point not found")
    if body.point_name is not None:
        mp.point_name = body.point_name
    if body.point_type is not None:
        mp.point_type = body.point_type
    if body.position_x_mm is not None:
        mp.position_x_mm = body.position_x_mm
    if body.position_y_mm is not None:
        mp.position_y_mm = body.position_y_mm
    if body.position_z_mm is not None:
        mp.position_z_mm = body.position_z_mm
    if body.bolt_pattern is not None:
        mp.bolt_pattern = body.bolt_pattern
    if body.torque_spec_nm is not None:
        mp.torque_spec_nm = body.torque_spec_nm
    if body.notes is not None:
        mp.notes = body.notes
    db.commit()
    db.refresh(mp)
    return _mount_to_response(mp)


@router.delete("/oem/mounting-points/{point_id}", status_code=204)
def delete_mounting_point(
    point_id: str,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    mp = db.query(OEMMountingPoint).filter(OEMMountingPoint.id == uuid.UUID(point_id)).first()
    if not mp:
        raise HTTPException(status_code=404, detail="Mounting point not found")
    db.delete(mp)
    db.commit()


# ── Routing Paths ──────────────────────────────────────────────────────


@router.get(
    "/oem/models/{model_id}/routing-paths",
    response_model=list[RoutingPathResponse],
)
def list_routing_paths(
    model_id: str,
    workshop_id: str | None = Depends(get_optional_workshop),
    db: Session = Depends(get_db),
):
    vm = db.query(OEMVehicleModel).filter(OEMVehicleModel.id == uuid.UUID(model_id)).first()
    if not vm:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    paths = db.query(OEMRoutingPath).filter(OEMRoutingPath.model_id == vm.id).all()
    return [_routing_to_response(p) for p in paths]


@router.post(
    "/oem/models/{model_id}/routing-paths",
    response_model=RoutingPathResponse,
    status_code=201,
)
def create_routing_path(
    model_id: str,
    body: RoutingPathCreate,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    vm = db.query(OEMVehicleModel).filter(OEMVehicleModel.id == uuid.UUID(model_id)).first()
    if not vm:
        raise HTTPException(status_code=404, detail="Vehicle model not found")
    rp = OEMRoutingPath(
        model_id=vm.id,
        path_name=body.path_name,
        path_type=body.path_type,
        start_point=body.start_point,
        end_point=body.end_point,
        length_estimate_mm=body.length_estimate_mm,
        constraints=body.constraints,
        notes=body.notes,
    )
    db.add(rp)
    db.commit()
    db.refresh(rp)
    return _routing_to_response(rp)


@router.put(
    "/oem/routing-paths/{path_id}",
    response_model=RoutingPathResponse,
)
def update_routing_path(
    path_id: str,
    body: RoutingPathUpdate,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    rp = db.query(OEMRoutingPath).filter(OEMRoutingPath.id == uuid.UUID(path_id)).first()
    if not rp:
        raise HTTPException(status_code=404, detail="Routing path not found")
    for field in ("path_name", "path_type", "start_point", "end_point", "length_estimate_mm", "constraints", "notes"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(rp, field, val)
    db.commit()
    db.refresh(rp)
    return _routing_to_response(rp)


@router.delete("/oem/routing-paths/{path_id}", status_code=204)
def delete_routing_path(
    path_id: str,
    workshop_id: str = Depends(get_current_workshop),
    db: Session = Depends(get_db),
):
    rp = db.query(OEMRoutingPath).filter(OEMRoutingPath.id == uuid.UUID(path_id)).first()
    if not rp:
        raise HTTPException(status_code=404, detail="Routing path not found")
    db.delete(rp)
    db.commit()


# ── Search / Lookup ────────────────────────────────────────────────────


@router.get("/oem/search", response_model=OEMLookupResponse)
def search_oem(
    workshop_id: str | None = Depends(get_optional_workshop),
    db: Session = Depends(get_db),
    make: str | None = Query(None),
    model: str | None = Query(None),
    year: int | None = Query(None),
    vehicle_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    query = (
        db.query(OEMVehicleModel)
        .join(OEMManufacturer)
        .options(joinedload(OEMVehicleModel.manufacturer))
    )
    if make:
        query = query.filter(OEMManufacturer.name.ilike(f"%{make}%"))
    if model:
        query = query.filter(OEMVehicleModel.model_name.ilike(f"%{model}%"))
    if year:
        query = query.filter(
            (OEMVehicleModel.year_start.is_(None) | (OEMVehicleModel.year_start <= year))
            & (OEMVehicleModel.year_end.is_(None) | (OEMVehicleModel.year_end >= year))
        )
    if vehicle_type:
        query = query.filter(OEMVehicleModel.vehicle_type == vehicle_type)
    total = query.count()
    results = query.order_by(OEMManufacturer.name, OEMVehicleModel.model_name).offset(offset).limit(limit).all()
    return OEMLookupResponse(
        models=[
            VehicleModelSearchResult(
                id=str(vm.id),
                manufacturer_id=str(vm.manufacturer_id),
                manufacturer_name=vm.manufacturer.name if vm.manufacturer else "",
                model_name=vm.model_name,
                generation=vm.generation,
                vehicle_type=vm.vehicle_type,
                year_start=vm.year_start,
                year_end=vm.year_end,
            )
            for vm in results
        ],
        total=total,
    )
