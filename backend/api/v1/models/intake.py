from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class IntakeResponse(BaseModel):
    intake_id: str
    status: str
    missing_views: list[str] = []
    low_quality_views: list[str] = []
    swap_suspected: bool = False
    attempts: dict[str, int] = {}
    quality_scores: dict[str, float] = {}
    failure_reason: Optional[str] = None
    oem_model_id: Optional[str] = None


class AnalyzeResponse(BaseModel):
    job_id: str
    status: str


class JobResponse(BaseModel):
    job_id: str
    status: str
    current_stage: Optional[str] = None
    progress_pct: int = 0
    assessment_state: Optional[str] = None
    completed_stages: list[str] = []
    missing_stages: list[str] = []
    result: Optional[dict] = None
    retry_count: int = 0
    retry_available: bool = False
    error_message: Optional[str] = None
    timed_out: bool = False
    infrastructure_degradation: list[dict] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConfirmRequest(BaseModel):
    confirmation_type: str
    selection: str


class IdentifyVehicleResponse(BaseModel):
    intake_id: str
    classification: dict
    suggestions: list[dict] = []


class SetOemModelRequest(BaseModel):
    oem_model_id: Optional[str] = None


class SetOemModelResponse(BaseModel):
    intake_id: str
    oem_model_id: Optional[str] = None


class ViewSlotResponse(BaseModel):
    intake_id: str
    view_slot: str
    status: str
    attempt: int
    blurry: bool = False
    missing_views: list[str] = []
    low_quality_views: list[str] = []
    swap_suspected: bool = False
    attempts: dict[str, int] = {}
    quality_scores: dict[str, float] = {}
    failure_reason: Optional[str] = None
