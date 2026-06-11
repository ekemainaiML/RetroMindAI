
from pydantic import BaseModel


class ManufacturerCreate(BaseModel):
    name: str
    country: str | None = None
    founded_year: int | None = None


class ManufacturerUpdate(BaseModel):
    name: str | None = None
    country: str | None = None
    founded_year: int | None = None
    is_active: bool | None = None


class ManufacturerResponse(BaseModel):
    id: str
    name: str
    country: str | None = None
    founded_year: int | None = None
    is_active: bool
    model_count: int = 0
    created_at: str


class VehicleModelCreate(BaseModel):
    manufacturer_id: str
    model_name: str
    generation: str | None = None
    vehicle_type: str
    year_start: int | None = None
    year_end: int | None = None
    image_url: str | None = None


class VehicleModelUpdate(BaseModel):
    model_name: str | None = None
    generation: str | None = None
    vehicle_type: str | None = None
    year_start: int | None = None
    year_end: int | None = None
    image_url: str | None = None
    is_active: bool | None = None


class VehicleModelResponse(BaseModel):
    id: str
    manufacturer_id: str
    manufacturer_name: str = ""
    model_name: str
    generation: str | None = None
    vehicle_type: str
    year_start: int | None = None
    year_end: int | None = None
    image_url: str | None = None
    is_active: bool
    spec_count: int = 0
    mounting_point_count: int = 0
    routing_path_count: int = 0
    created_at: str


class SpecificationCreate(BaseModel):
    model_id: str
    wheelbase_mm: int | None = None
    overall_length_mm: int | None = None
    overall_width_mm: int | None = None
    overall_height_mm: int | None = None
    ground_clearance_mm: int | None = None
    cargo_length_mm: int | None = None
    cargo_width_mm: int | None = None
    kerb_weight_kg: int | None = None
    gross_weight_kg: int | None = None
    payload_kg: int | None = None
    seating_capacity: int | None = None
    engine_cc: int | None = None
    fuel_type: str | None = None
    notes: str | None = None


class SpecificationUpdate(BaseModel):
    wheelbase_mm: int | None = None
    overall_length_mm: int | None = None
    overall_width_mm: int | None = None
    overall_height_mm: int | None = None
    ground_clearance_mm: int | None = None
    cargo_length_mm: int | None = None
    cargo_width_mm: int | None = None
    kerb_weight_kg: int | None = None
    gross_weight_kg: int | None = None
    payload_kg: int | None = None
    seating_capacity: int | None = None
    engine_cc: int | None = None
    fuel_type: str | None = None
    notes: str | None = None


class SpecificationResponse(BaseModel):
    id: str
    model_id: str
    wheelbase_mm: int | None = None
    overall_length_mm: int | None = None
    overall_width_mm: int | None = None
    overall_height_mm: int | None = None
    ground_clearance_mm: int | None = None
    cargo_length_mm: int | None = None
    cargo_width_mm: int | None = None
    kerb_weight_kg: int | None = None
    gross_weight_kg: int | None = None
    payload_kg: int | None = None
    seating_capacity: int | None = None
    engine_cc: int | None = None
    fuel_type: str | None = None
    notes: str | None = None
    created_at: str


class MountingPointCreate(BaseModel):
    model_id: str
    point_name: str
    point_type: str
    position_x_mm: int | None = None
    position_y_mm: int | None = None
    position_z_mm: int | None = None
    bolt_pattern: str | None = None
    torque_spec_nm: int | None = None
    notes: str | None = None


class MountingPointUpdate(BaseModel):
    point_name: str | None = None
    point_type: str | None = None
    position_x_mm: int | None = None
    position_y_mm: int | None = None
    position_z_mm: int | None = None
    bolt_pattern: str | None = None
    torque_spec_nm: int | None = None
    notes: str | None = None


class MountingPointResponse(BaseModel):
    id: str
    model_id: str
    point_name: str
    point_type: str
    position_x_mm: int | None = None
    position_y_mm: int | None = None
    position_z_mm: int | None = None
    bolt_pattern: str | None = None
    torque_spec_nm: int | None = None
    notes: str | None = None
    created_at: str


class RoutingPathCreate(BaseModel):
    model_id: str
    path_name: str
    path_type: str
    start_point: str | None = None
    end_point: str | None = None
    length_estimate_mm: int | None = None
    constraints: dict | None = None
    notes: str | None = None


class RoutingPathUpdate(BaseModel):
    path_name: str | None = None
    path_type: str | None = None
    start_point: str | None = None
    end_point: str | None = None
    length_estimate_mm: int | None = None
    constraints: dict | None = None
    notes: str | None = None


class RoutingPathResponse(BaseModel):
    id: str
    model_id: str
    path_name: str
    path_type: str
    start_point: str | None = None
    end_point: str | None = None
    length_estimate_mm: int | None = None
    constraints: dict | None = None
    notes: str | None = None
    created_at: str


class VehicleModelSearchResult(BaseModel):
    id: str
    manufacturer_id: str
    manufacturer_name: str
    model_name: str
    generation: str | None = None
    vehicle_type: str
    year_start: int | None = None
    year_end: int | None = None


class OEMLookupRequest(BaseModel):
    make: str | None = None
    model: str | None = None
    year: int | None = None
    vehicle_type: str | None = None


class OEMLookupResponse(BaseModel):
    models: list[VehicleModelSearchResult]
    total: int
