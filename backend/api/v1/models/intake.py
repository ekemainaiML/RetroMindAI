
from pydantic import BaseModel


class IntakeResponse(BaseModel):
    intake_id: str
    status: str
    missing_views: list[str] = []
    low_quality_views: list[str] = []
    occluded_views: list[str] = []
    swap_suspected: bool = False
    attempts: dict[str, int | None] = {}
    quality_scores: dict[str, float | None] = {}
    failure_reason: str | None = None
    oem_model_id: str | None = None


class AnalyzeResponse(BaseModel):
    job_id: str
    status: str


class JobResponse(BaseModel):
    job_id: str
    status: str
    current_stage: str | None = None
    progress_pct: int = 0
    assessment_state: str | None = None
    completed_stages: list[str] = []
    missing_stages: list[str] = []
    result: dict | None = None
    retry_count: int = 0
    retry_available: bool = False
    error_message: str | None = None
    timed_out: bool = False
    infrastructure_degradation: list[dict] = []
    created_at: str | None = None
    updated_at: str | None = None


class ConfirmRequest(BaseModel):
    confirmation_type: str
    selection: str


class IdentifyVehicleResponse(BaseModel):
    intake_id: str
    classification: dict
    suggestions: list[dict] = []


class SetOemModelRequest(BaseModel):
    oem_model_id: str | None = None


class SetOemModelResponse(BaseModel):
    intake_id: str
    oem_model_id: str | None = None


class ViewSlotResponse(BaseModel):
    intake_id: str
    view_slot: str
    status: str
    attempt: int
    blurry: bool = False
    occluded: bool = False
    missing_views: list[str] = []
    low_quality_views: list[str] = []
    swap_suspected: bool = False
    attempts: dict[str, int | None] = {}
    quality_scores: dict[str, float | None] = {}
    failure_reason: str | None = None
