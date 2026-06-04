from typing import Optional

from pydantic import BaseModel


class ManufacturerCreate(BaseModel):
    name: str
    country: Optional[str] = None
    founded_year: Optional[int] = None


class ManufacturerUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    founded_year: Optional[int] = None
    is_active: Optional[bool] = None


class ManufacturerResponse(BaseModel):
    id: str
    name: str
    country: Optional[str] = None
    founded_year: Optional[int] = None
    is_active: bool
    model_count: int = 0
    created_at: str


class VehicleModelCreate(BaseModel):
    manufacturer_id: str
    model_name: str
    generation: Optional[str] = None
    vehicle_type: str
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    image_url: Optional[str] = None


class VehicleModelUpdate(BaseModel):
    model_name: Optional[str] = None
    generation: Optional[str] = None
    vehicle_type: Optional[str] = None
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class VehicleModelResponse(BaseModel):
    id: str
    manufacturer_id: str
    manufacturer_name: str = ""
    model_name: str
    generation: Optional[str] = None
    vehicle_type: str
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    image_url: Optional[str] = None
    is_active: bool
    spec_count: int = 0
    mounting_point_count: int = 0
    routing_path_count: int = 0
    created_at: str


class SpecificationCreate(BaseModel):
    model_id: str
    wheelbase_mm: Optional[int] = None
    overall_length_mm: Optional[int] = None
    overall_width_mm: Optional[int] = None
    overall_height_mm: Optional[int] = None
    ground_clearance_mm: Optional[int] = None
    cargo_length_mm: Optional[int] = None
    cargo_width_mm: Optional[int] = None
    kerb_weight_kg: Optional[int] = None
    gross_weight_kg: Optional[int] = None
    payload_kg: Optional[int] = None
    seating_capacity: Optional[int] = None
    engine_cc: Optional[int] = None
    fuel_type: Optional[str] = None
    notes: Optional[str] = None


class SpecificationUpdate(BaseModel):
    wheelbase_mm: Optional[int] = None
    overall_length_mm: Optional[int] = None
    overall_width_mm: Optional[int] = None
    overall_height_mm: Optional[int] = None
    ground_clearance_mm: Optional[int] = None
    cargo_length_mm: Optional[int] = None
    cargo_width_mm: Optional[int] = None
    kerb_weight_kg: Optional[int] = None
    gross_weight_kg: Optional[int] = None
    payload_kg: Optional[int] = None
    seating_capacity: Optional[int] = None
    engine_cc: Optional[int] = None
    fuel_type: Optional[str] = None
    notes: Optional[str] = None


class SpecificationResponse(BaseModel):
    id: str
    model_id: str
    wheelbase_mm: Optional[int] = None
    overall_length_mm: Optional[int] = None
    overall_width_mm: Optional[int] = None
    overall_height_mm: Optional[int] = None
    ground_clearance_mm: Optional[int] = None
    cargo_length_mm: Optional[int] = None
    cargo_width_mm: Optional[int] = None
    kerb_weight_kg: Optional[int] = None
    gross_weight_kg: Optional[int] = None
    payload_kg: Optional[int] = None
    seating_capacity: Optional[int] = None
    engine_cc: Optional[int] = None
    fuel_type: Optional[str] = None
    notes: Optional[str] = None
    created_at: str


class MountingPointCreate(BaseModel):
    model_id: str
    point_name: str
    point_type: str
    position_x_mm: Optional[int] = None
    position_y_mm: Optional[int] = None
    position_z_mm: Optional[int] = None
    bolt_pattern: Optional[str] = None
    torque_spec_nm: Optional[int] = None
    notes: Optional[str] = None


class MountingPointUpdate(BaseModel):
    point_name: Optional[str] = None
    point_type: Optional[str] = None
    position_x_mm: Optional[int] = None
    position_y_mm: Optional[int] = None
    position_z_mm: Optional[int] = None
    bolt_pattern: Optional[str] = None
    torque_spec_nm: Optional[int] = None
    notes: Optional[str] = None


class MountingPointResponse(BaseModel):
    id: str
    model_id: str
    point_name: str
    point_type: str
    position_x_mm: Optional[int] = None
    position_y_mm: Optional[int] = None
    position_z_mm: Optional[int] = None
    bolt_pattern: Optional[str] = None
    torque_spec_nm: Optional[int] = None
    notes: Optional[str] = None
    created_at: str


class RoutingPathCreate(BaseModel):
    model_id: str
    path_name: str
    path_type: str
    start_point: Optional[str] = None
    end_point: Optional[str] = None
    length_estimate_mm: Optional[int] = None
    constraints: Optional[dict] = None
    notes: Optional[str] = None


class RoutingPathUpdate(BaseModel):
    path_name: Optional[str] = None
    path_type: Optional[str] = None
    start_point: Optional[str] = None
    end_point: Optional[str] = None
    length_estimate_mm: Optional[int] = None
    constraints: Optional[dict] = None
    notes: Optional[str] = None


class RoutingPathResponse(BaseModel):
    id: str
    model_id: str
    path_name: str
    path_type: str
    start_point: Optional[str] = None
    end_point: Optional[str] = None
    length_estimate_mm: Optional[int] = None
    constraints: Optional[dict] = None
    notes: Optional[str] = None
    created_at: str


class VehicleModelSearchResult(BaseModel):
    id: str
    manufacturer_id: str
    manufacturer_name: str
    model_name: str
    generation: Optional[str] = None
    vehicle_type: str
    year_start: Optional[int] = None
    year_end: Optional[int] = None


class OEMLookupRequest(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    vehicle_type: Optional[str] = None


class OEMLookupResponse(BaseModel):
    models: list[VehicleModelSearchResult]
    total: int
