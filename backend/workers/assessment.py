import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone as tz

import numpy as np

from sqlalchemy.orm import Session as DBSession, joinedload

from core.compliance import compute_compliance_state
from core.confidence import ConfidenceEngine
from core.conflict import evaluate_classification_conflict
from core.database import SessionLocal
from core.degradation import get_degradation_manager
from core.config import settings
from ai.classification.preprocess import auto_enhance, check_occlusion, detect_low_light
from core.risk import (
    assess_deviation_risks,
    compute_system_risk_state,
    create_risk_record,
)

_logged_rec_engine_warning = False

logger = logging.getLogger(__name__)

_classifier = None
_geometry_extractor = None
_deviation_detector = None
_deviation_detector_kwargs: dict = {}
_recommendation_engine = None


def _get_classifier():
    global _classifier
    if _classifier is None:
        from ai.classification.classifier import VehicleClassifier
        _classifier = VehicleClassifier()
    return _classifier


def _get_geometry_extractor():
    global _geometry_extractor
    if _geometry_extractor is None:
        from ai.geometry.extractor import GeometryExtractor
        _geometry_extractor = GeometryExtractor()
    return _geometry_extractor


def _get_deviation_detector():
    global _deviation_detector
    if _deviation_detector is None:
        from ai.deviation.detector import DeviationDetector
        _deviation_detector = DeviationDetector(**_deviation_detector_kwargs)
    return _deviation_detector


def _reset_deviation_detector(oem_specs: dict | None = None):
    global _deviation_detector, _deviation_detector_kwargs
    _deviation_detector = None
    _deviation_detector_kwargs = {}
    if oem_specs:
        _deviation_detector_kwargs["oem_specs"] = oem_specs


def _get_recommendation_engine():
    global _recommendation_engine
    if _recommendation_engine is None:
        from ai.recommendations.engine import RecommendationEngine
        _recommendation_engine = RecommendationEngine()
    return _recommendation_engine


def _get_deg_mgr():
    return get_degradation_manager()


def _fetch_oem_specs(model_id: uuid.UUID | None, vehicle_type: str, db: DBSession) -> dict | None:
    if not model_id:
        return None
    try:
        from core.models import OEMSpecification
        spec = (
            db.query(OEMSpecification)
            .filter(OEMSpecification.model_id == model_id)
            .first()
        )
        if not spec:
            logger.warning("No OEM specs found for model %s", model_id)
            return None
        result = {
            "_vehicle_type": vehicle_type,
            "wheelbase_mm": spec.wheelbase_mm,
            "overall_length_mm": spec.overall_length_mm,
            "overall_width_mm": spec.overall_width_mm,
            "ground_clearance_mm": spec.ground_clearance_mm,
            "cargo_length_mm": spec.cargo_length_mm,
        }
        logger.info("Hydrated deviation references from OEM specs for model %s", model_id)
        return result
    except Exception:
        logger.exception("Failed to fetch OEM specs for model %s (non-fatal)", model_id)
        return None


def _fetch_oem_zones(model_id: uuid.UUID | None, db: DBSession) -> list[dict] | None:
    if not model_id:
        return None
    try:
        from core.models import OEMMountingPoint, OEMRoutingPath
        points = db.query(OEMMountingPoint).filter(OEMMountingPoint.model_id == model_id).all()
        paths = db.query(OEMRoutingPath).filter(OEMRoutingPath.model_id == model_id).all()
        return {"mounting_points": points, "routing_paths": paths}  # type: ignore[return-value]
    except Exception:
        logger.exception("Failed to fetch OEM zones for model %s", model_id)
        return None


STAGE_TIMEOUTS = {
    "vehicle_classification": 20,
    "geometry_extraction": 15,
    "deviation_detection": 20,
    "confidence_scoring": 5,
    "recommendations": 5,
    "battery_optimization": 20,
    "wiring_generation": 20,
    "digital_twin": 10,
}


def _run_stage_with_timeout(stage_fn, stage_name, timeout_seconds, *args):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(stage_fn, *args)
        try:
            result = future.result(timeout=timeout_seconds)
            logger.info("Stage '%s' completed in under %ds", stage_name, timeout_seconds)
            return True, result
        except FuturesTimeoutError:
            logger.error("Stage '%s' timed out after %ds", stage_name, timeout_seconds)
            return False, None
        except Exception as e:
            logger.error("Stage '%s' failed: %s", stage_name, e)
            return False, None


ASSESSMENT_STAGES = [
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
]

REQUIRED_SLOTS = ["left_side_profile", "right_side_profile", "rear_view"]
ALL_SLOTS = REQUIRED_SLOTS + ["front_view", "engine_bay", "underbody"]

SOFT_TIMEOUT_SECONDS = 90
HARD_TIMEOUT_SECONDS = 120

MIN_STAGES_FOR_PARTIAL = {
    "vehicle_classification",
    "geometry_extraction",
    "deviation_detection",
}

STAGE_SLEEP_SECONDS = 1.0


def _compute_factors(
    intake, oem_model_id: uuid.UUID | None = None, db: DBSession | None = None,
) -> tuple[dict[str, float], list[str], list[str], dict | None, dict | None, dict | None]:
    view_slots = intake.view_slots or {}
    missing_views = [s for s in REQUIRED_SLOTS if view_slots.get(s) is None]
    low_quality_views = list(intake.low_quality_views or [])

    present = len(REQUIRED_SLOTS) - len(missing_views)
    completeness = (present / len(REQUIRED_SLOTS)) * 100.0

    quality = max(0.0, 100.0 - (len(low_quality_views) * 33.0))

    available = sum(1 for s in ALL_SLOTS if view_slots.get(s) is not None)
    visibility = (available / len(ALL_SLOTS)) * 100.0

    classification = 85.0
    geometry = 70.0
    deviation_certainty = 65.0

    deg_mgr = _get_deg_mgr()
    classification_result = None
    geometry_result = None
    deviation_result = None
    image_paths = {k: v for k, v in view_slots.items() if v is not None}
    if image_paths:
        downscaled = {}
        for view, path in image_paths.items():
            from ai.downscale import downscale_if_large
            dp = downscale_if_large(path)
            if dp != path:
                downscaled[view] = dp
        if downscaled:
            image_paths.update(downscaled)
            logger.info("Downscaled %d image(s) for processing", len(downscaled))

        enhanced_views = list(intake.enhanced_views or [])
        for view, path in list(image_paths.items()):
            if detect_low_light(path):
                enhanced_path = auto_enhance(path)
                if enhanced_path:
                    image_paths[view] = enhanced_path
                    if view not in enhanced_views:
                        enhanced_views.append(view)
                    logger.info("Auto-enhanced %s (low light)", view)
        if enhanced_views:
            intake.enhanced_views = enhanced_views
            if db:
                db.add(intake)
                db.commit()
                db.refresh(intake)
            logger.info("Enhanced %d low-light view(s): %s", len(enhanced_views), enhanced_views)

        occluded_views = list(intake.occluded_views or [])
        for view, path in image_paths.items():
            occ_result = check_occlusion(path)
            if occ_result.get("occluded") and view not in occluded_views:
                occluded_views.append(view)
        if occluded_views != list(intake.occluded_views or []):
            intake.occluded_views = occluded_views
            if db:
                db.add(intake)
                db.commit()
                db.refresh(intake)

        if deg_mgr.should_skip_stage("vehicle_classification"):
            logger.warning("Skipping vehicle_classification (degradation)")
        else:
            success, result = _run_stage_with_timeout(
                _get_classifier().classify,
                "vehicle_classification",
                STAGE_TIMEOUTS["vehicle_classification"],
                image_paths,
            )
            if success:
                classification_result = result
                classification = classification_result["confidence"] * 100.0
            else:
                deg_mgr.register("onnx_runner", 1, "Vehicle classification stage failed or timed out")

        vehicle_type = (
            classification_result.get("vehicle_type", "three_wheeler")
            if classification_result
            else "three_wheeler"
        )

        if deg_mgr.should_skip_stage("geometry_extraction"):
            logger.warning("Skipping geometry_extraction (degradation)")
        else:
            success, result = _run_stage_with_timeout(
                _get_geometry_extractor().extract,
                "geometry_extraction",
                STAGE_TIMEOUTS["geometry_extraction"],
                image_paths,
                vehicle_type,
            )
            if success:
                geometry_result = result
                geometry = geometry_result["geometry_score"]
                visibility = geometry_result["avg_structural_coverage"] * 100.0
            else:
                deg_mgr.register("opencv_processor", 1, "Geometry extraction stage failed or timed out")

        if deg_mgr.should_skip_stage("deviation_detection"):
            logger.warning("Skipping deviation_detection (degradation)")
        else:
            oem_specs = _fetch_oem_specs(oem_model_id, vehicle_type, db) if oem_model_id and db else None
            if oem_specs:
                _reset_deviation_detector(oem_specs)
            success, result = _run_stage_with_timeout(
                _get_deviation_detector().detect,
                "deviation_detection",
                STAGE_TIMEOUTS["deviation_detection"],
                image_paths,
                vehicle_type,
            )
            if success:
                deviation_result = result
                deviation_certainty = deviation_result["deviation_certainty"]
            else:
                deg_mgr.register("deviation_detector", 1, "Deviation detection stage failed or timed out")

    return (
        {
            "completeness": completeness,
            "quality": quality,
            "visibility": visibility,
            "classification": classification,
            "geometry": geometry,
            "deviation_certainty": deviation_certainty,
        },
        missing_views,
        low_quality_views,
        classification_result,
        geometry_result,
        deviation_result,
    )


def _make_json_safe(obj):
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_json_safe(v) for v in obj]
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return _make_json_safe(obj.tolist())
    return obj


def _build_intake_data(
    intake,
    factors: dict[str, float],
    missing_views: list[str],
) -> dict:
    mandatory_view_quality: dict[str, float | None] = {}
    for slot in REQUIRED_SLOTS:
        if slot in missing_views:
            mandatory_view_quality[slot] = None
        else:
            qs = (intake.quality_scores or {}).get(slot)
            mandatory_view_quality[slot] = qs if qs is not None else None

    return {
        "missing_views": missing_views,
        "mandatory_view_quality": mandatory_view_quality,
        "classification": factors["classification"],
        "geometry": factors["geometry"],
    }


def _build_risks(
    low_quality_views: list[str],
    missing_views: list[str],
    swap_detected: bool,
    deviation_result: dict | None = None,
) -> list[dict]:
    risks: list[dict] = []
    for view in low_quality_views:
        risks.append(
            create_risk_record(
                category="image_quality",
                severity="medium",
                message=f"Low quality view: {view}",
                recommendation="Re-upload with better lighting and focus",
                blocking=False,
                confidence=0.70,
            )
        )
    for view in missing_views:
        risks.append(
            create_risk_record(
                category="missing_view",
                severity="high",
                message=f"Missing mandatory view: {view}",
                recommendation="Upload the missing view to improve assessment completeness",
                blocking=True,
                confidence=0.95,
            )
        )
    if swap_detected:
        risks.append(
            create_risk_record(
                category="swap_detected",
                severity="low",
                message="Left/right side profile swap suspected",
                recommendation="Verify image orientation and re-upload if incorrect",
                blocking=False,
                confidence=0.60,
            )
        )
    risks.extend(assess_deviation_risks(deviation_result))
    return risks


def _build_result(
    factors: dict[str, float],
    score: float,
    state: str,
    override_reasons: list[str],
    risks: list[dict],
    risk_state: str,
    intake,
    classification_result: dict | None = None,
    geometry_result: dict | None = None,
    deviation_result: dict | None = None,
    degradations: list[dict] | None = None,
) -> dict:
    deviation_anomalies = 0
    deviation_severity = "low"
    if deviation_result:
        deviation_anomalies = deviation_result.get("deviation_count", 0)
        dscore = deviation_result.get("deviation_score", 100)
        if dscore >= 80:
            deviation_severity = "low"
        elif dscore >= 50:
            deviation_severity = "medium"
        else:
            deviation_severity = "high"

    feasibility_base = max(30, int(score) - 6)

    classification_conf_pct = factors.get("classification", 85)
    classification_conf = round(classification_conf_pct / 100, 2)

    if classification_result:
        alternatives_conflict = [
            {"vehicle_type": a["type"], "confidence": a["confidence"]}
            for a in classification_result.get("alternatives", [])
        ]
        vc_type = classification_result.get("vehicle_type", "three_wheeler")
        vc_human = classification_result.get("human_confirmed", False)
    else:
        alternatives_conflict = [
            {"vehicle_type": "three_wheeler", "confidence": classification_conf},
            {"vehicle_type": "motorcycle", "confidence": round(1 - classification_conf, 2)},
        ]
        vc_type = "three_wheeler"
        vc_human = False

    geometry_consistency = factors.get("geometry", 70)
    if geometry_result and geometry_result.get("geometry_conflict"):
        geometry_consistency = min(geometry_consistency, 30)

    conflict = evaluate_classification_conflict(
        classification_conf=classification_conf_pct,
        alternatives=list(alternatives_conflict),
        geometry_consistency=geometry_consistency,
        mandatory_view_quality={
            s: (intake.quality_scores or {}).get(s)
            for s in REQUIRED_SLOTS
        },
    )

    geometry_extraction = None
    if geometry_result:
        geometry_extraction = {
            k: v for k, v in geometry_result.items()
            if k != "avg_structural_coverage"
        }

    needs_confirmation = conflict["action"] == "human_confirmation"
    confirmation_required = None
    if needs_confirmation:
        classification_conf_pct_int = int(round(classification_conf_pct))
        options = (conflict.get("options") or []) or [
            {"vehicle_type": a["vehicle_type"], "confidence": a["confidence"]}
            for a in alternatives_conflict
        ]
        confirmation_required = {
            "type": "vehicle_classification",
            "message": f"Vehicle classified as '{vc_type}' with {classification_conf_pct_int}% confidence. Confirm or select an alternative:",
            "options": [
                o["vehicle_type"] for o in options
            ],
            "current_value": vc_type,
        }

    frontend_deviations = []
    if deviation_result:
        for dev in deviation_result.get("deviations", []):
            frontend_deviations.append({
                "component": dev.get("parameter", "unknown"),
                "severity": (
                    "critical" if dev.get("severity") == "major"
                    else "medium" if dev.get("severity") == "moderate"
                    else dev.get("severity", "low")
                ),
                "description": dev.get("notes", ""),
                "reference": dev.get("reference"),
                "estimated": dev.get("estimated"),
                "delta": dev.get("delta"),
                "delta_pct": dev.get("delta_pct"),
            })

    result = {
        "assessment_state": state,
        "confidence_score": int(round(score)),
        "confidence_factors": {
            k: int(round(v)) for k, v in factors.items()
        },
        "safety_overrides": override_reasons,
        "feasibility_score": feasibility_base,
        "feasibility_label": (
            "feasible_with_adaptation"
            if score >= 60
            else "conditionally_feasible"
        ),
        "vehicle_classification": {
            "type": vc_type,
            "confidence": classification_conf,
            "human_confirmed": vc_human,
            "classifier": (
                classification_result.get("classifier_used", "ONNX") if classification_result else "N/A"
            ) if classification_result else "N/A",
            "alternatives": list(alternatives_conflict),
            "model_loaded": classification_result.get("model_loaded", False) if classification_result else False,
        },
        "geometry_extraction": geometry_extraction,
        "deviation_summary": {
            "anomalies_detected": deviation_anomalies,
            "severity": deviation_severity,
            "top_issues": [
                d["notes"]
                for d in (deviation_result.get("deviations", []) if deviation_result else [])
                if d.get("severity") in ("moderate", "major")
            ],
        },
        "deviation_result": deviation_result,
        "risk_summary": {
            "system_risk_state": risk_state,
            "critical_count": sum(
                1 for r in risks if r.get("severity") == "critical"
            ),
            "high_count": sum(1 for r in risks if r.get("severity") == "high"),
            "medium_count": sum(
                1 for r in risks if r.get("severity") == "medium"
            ),
            "low_count": sum(1 for r in risks if r.get("severity") == "low"),
        },
        "risks": risks,
        "risk_register": risks,
        "deviations": frontend_deviations,
        "needs_confirmation": needs_confirmation,
        "confirmation_required": confirmation_required,
        "compliance_state": compute_compliance_state(
            assessment_state=state,
            risk_state=risk_state,
            risk_counts={
                "critical": sum(1 for r in risks if r.get("severity") == "critical"),
                "high": sum(1 for r in risks if r.get("severity") == "high"),
                "medium": sum(1 for r in risks if r.get("severity") == "medium"),
                "low": sum(1 for r in risks if r.get("severity") == "low"),
            },
            missing_views=[
                s for s in REQUIRED_SLOTS
                if (intake.view_slots or {}).get(s) is None
            ],
            critical_deviations=(deviation_result or {}).get("critical_delamination", False),
            deviation_count=(deviation_result or {}).get("deviation_count", 0),
            confidence_score=int(round(score)),
        ),
        "degradations": degradations or [],
    }
    if degradations:
        highest_tier = max(d.get("tier", 0) for d in degradations)
        if highest_tier >= 3:
            result["assessment_state"] = "inconclusive"
            result["confidence_score"] = 0
    return result


def run_assessment(intake_id: str) -> None:
    from core.feature_flags import FeatureFlagStore
    FeatureFlagStore.load_overrides()

    from core.models import Intake, Job

    if settings.enable_optuna:
        try:
            from optimization.hyperparameter.config_overrides import ConfigOverrides
            ConfigOverrides.apply()
        except Exception:
            logger.warning("Optuna config overrides failed (non-fatal)")

    db = SessionLocal()
    try:
        intake_uuid = uuid.UUID(intake_id)
        job = (
            db.query(Job)
            .filter(
                Job.intake_id == intake_uuid,
                Job.status.in_(["queued", "retrying"]),
            )
            .order_by(Job.created_at.desc())
            .first()
        )
        if not job:
            logger.warning("No active job found for intake %s", intake_id)
            return

        job_uuid = job.id

        if job.status == "retrying":
            job.status = "running"
            job.current_stage = None
            job.progress_pct = 0
            job.completed_stages = []
            job.result = None
            job.error_message = None
            db.commit()
        else:
            job.status = "running"
            db.commit()

        created_at = job.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=tz.utc)

        intake = db.query(Intake).filter(Intake.id == intake_uuid).first()
        missing_views: list[str] = []
        low_quality_views: list[str] = []
        if intake:
            view_slots = intake.view_slots or {}
            missing_views = [s for s in REQUIRED_SLOTS if view_slots.get(s) is None]
            low_quality_views = list(intake.low_quality_views or [])

        stage_filter = set(missing_views + low_quality_views)
        reduced_stages = [s for s in ASSESSMENT_STAGES if s not in stage_filter]
        if not reduced_stages:
            reduced_stages = ASSESSMENT_STAGES[:3]

        total_stages = len(ASSESSMENT_STAGES)
        completed: list[str] = []
        soft_warning_shown = False

        for stage in reduced_stages:
            elapsed = (datetime.now(tz.utc) - created_at).total_seconds()

            if elapsed > HARD_TIMEOUT_SECONDS:
                _handle_timeout(job, db, completed, total_stages, intake_id)
                return

            if elapsed > SOFT_TIMEOUT_SECONDS and not soft_warning_shown:
                logger.warning(
                    "Job %s soft timeout exceeded (%.0fs)", job_uuid, elapsed
                )
                soft_warning_shown = True

            time.sleep(STAGE_SLEEP_SECONDS)

            job.current_stage = stage
            if stage not in completed:
                completed.append(stage)
            job.completed_stages = list(completed)
            job.progress_pct = min(int((len(completed) / total_stages) * 100), 100)
            job.updated_at = datetime.now(tz.utc)
            db.commit()

            from core.sse import publish_job_event
            publish_job_event(intake_id, "job.progress", {
                "job_id": str(job_uuid),
                "status": job.status,
                "current_stage": stage,
                "progress_pct": job.progress_pct,
                "completed_stages": list(completed),
            })

        deg_mgr = _get_deg_mgr()
        intake_model_id = intake.oem_model_id if intake else None
        factors, missing_views, low_quality_views, classification_result, geometry_result, deviation_result = _compute_factors(
            intake, oem_model_id=intake_model_id, db=db,
        )
        intake_data = _build_intake_data(intake, factors, missing_views)

        score = ConfidenceEngine.compute_score(factors)
        state = ConfidenceEngine.get_state(score)
        final_state = ConfidenceEngine.apply_safety_overrides(state, intake_data)

        override_reasons: list[str] = []
        if final_state != state:
            override_reasons.append(
                f"Safety override: {state} -> {final_state}"
            )

        swap_detected = intake.swap_detected if intake else False
        risks = _build_risks(low_quality_views, missing_views, swap_detected, deviation_result)
        risk_state = compute_system_risk_state(risks)

        degradations = deg_mgr.get_degradation_summary()

        battery_placement_data = None
        wiring_guidance_data = None
        if classification_result:
            vtype = classification_result.get("vehicle_type", "three_wheeler")
            try:
                from optimization.battery import compute_battery_zones
                from optimization.wiring import compute_routing

                oem_model_data = None
                if intake_model_id:
                    oem_model_data = _fetch_oem_zones(intake_model_id, db)

                def _run_battery():
                    return compute_battery_zones(
                        vehicle_type=vtype,
                        deviation_result=deviation_result,
                        geometry_result=geometry_result,
                        oem_data=oem_model_data,
                    )

                bat_success, bat_result = _run_stage_with_timeout(
                    _run_battery, "battery_optimization", STAGE_TIMEOUTS.get("battery_optimization", 5)
                )
                if bat_success and bat_result:
                    battery_placement_data = bat_result

                def _run_wiring():
                    return compute_routing(
                        vehicle_type=vtype,
                        battery_zone_id=(
                            battery_placement_data.get("recommended_zone")
                            if battery_placement_data else None
                        ),
                        deviation_result=deviation_result,
                        geometry_result=geometry_result,
                        oem_data=oem_model_data,
                    )

                wir_success, wir_result = _run_stage_with_timeout(
                    _run_wiring, "wiring_generation", STAGE_TIMEOUTS.get("wiring_generation", 5)
                )
                if wir_success and wir_result:
                    wiring_guidance_data = wir_result
            except Exception:
                logger.exception("Battery/wiring optimization failed (non-fatal)")
        job.status = "completed"
        job.current_stage = None
        job.progress_pct = 100
        try:
            job.result = _build_result(
                factors,
                score,
                final_state,
                override_reasons,
                risks,
                risk_state,
                intake,
                classification_result,
                geometry_result,
                deviation_result,
                degradations,
            )
        except Exception:
            logger.exception("Error building result")
            job.result = None
            job.status = "failed"

        if job.result:
            if battery_placement_data:
                job.result["battery_placement"] = battery_placement_data
            if wiring_guidance_data:
                job.result["wiring_guidance"] = wiring_guidance_data
            enhanced = []
            for view_name in list(intake.enhanced_views or []):
                original_path = (intake.view_slots or {}).get(view_name)
                if original_path:
                    base, ext = os.path.splitext(original_path)
                    enhanced_path = f"{base}_enhanced{ext}"
                    enhanced.append({
                        "view": view_name,
                        "original_url": original_path.replace("/app/uploads", "/uploads"),
                        "enhanced_url": enhanced_path.replace("/app/uploads", "/uploads"),
                    })
            if enhanced:
                job.result["enhanced_views"] = enhanced

        if job.result and job.status == "completed":
            try:
                engine = _get_recommendation_engine()
                vehicle_type = job.result["vehicle_classification"]["type"]
                deviation_severity = job.result["deviation_summary"]["severity"]
                assessment_for_engine: dict = {}
                if deviation_result:
                    assessment_for_engine["deviation_result"] = deviation_result
                if geometry_result:
                    assessment_for_engine["geometry_result"] = geometry_result

                oem_info = None
                if intake_model_id:
                    try:
                        from core.models import OEMVehicleModel
                        oem_vm = (
                            db.query(OEMVehicleModel)
                            .options(joinedload(OEMVehicleModel.manufacturer))
                            .filter(OEMVehicleModel.id == intake_model_id)
                            .first()
                        )
                        if oem_vm:
                            oem_info = {
                                "model_name": oem_vm.model_name,
                                "manufacturer_name": oem_vm.manufacturer.name if oem_vm.manufacturer else "",
                            }
                    except Exception:
                        logger.warning("Failed to fetch OEM model info (non-fatal)")

                def _run_recs():
                    return engine.generate(
                        assessment_result=assessment_for_engine,
                        vehicle_type=vehicle_type,
                        deviation_severity=deviation_severity,
                        factors=factors,
                        oem_info=oem_info,
                    )

                rec_success, rec_result = _run_stage_with_timeout(
                    _run_recs,
                    "recommendations",
                    STAGE_TIMEOUTS["recommendations"],
                )
                if rec_success and rec_result:
                    job.result["recommendations"] = rec_result["recommendations"]
                    job.result["feasibility_score"] = rec_result["feasibility_score"]
                    job.result["feasibility_label"] = (
                        "feasible_with_adaptation"
                        if rec_result["feasibility_score"] >= 60
                        else "conditionally_feasible"
                    )
                    job.result["estimated_total_cost_inr"] = rec_result["estimated_total_cost_inr"]
                    job.result["tooling_required"] = rec_result["tooling_required"]
                    job.result["skill_level_required"] = rec_result["skill_level_required"]
                    job.result["estimated_days"] = rec_result["estimated_days"]
                else:
                    deg_mgr.register("recommendation_engine", 1, "Recommendation engine failed or timed out")
                    job.result["degradations"] = deg_mgr.get_degradation_summary()

                if rec_success and rec_result and battery_placement_data:
                    for rec in job.result.get("recommendations", []):
                        if rec.get("id") == "battery_pack_location" and battery_placement_data.get("zones"):
                            top = battery_placement_data["zones"][0]
                            rec["title"] = top["label"]
                            rec["description"] = top["description"]
                            rec["zone_id"] = top["id"]
                            rec["zone_position"] = top["position"]
                            if top.get("adaptation_reason"):
                                rec["rationale"] = rec.get("rationale", []) + [top["adaptation_reason"]]
                        if rec.get("id") == "wiring_harness" and wiring_guidance_data:
                            rec["routing_path"] = wiring_guidance_data.get("routing_path")
                            rec["confidence"] = wiring_guidance_data.get("confidence", "partial")
                            if wiring_guidance_data.get("caution_zones"):
                                rec["caution_zones"] = wiring_guidance_data["caution_zones"]
            except Exception:
                logger.exception("Recommendation engine failed, results will be absent")

        if job.result and job.status == "completed":
            try:
                from ai.digital_twin.data import DigitalTwinDataGenerator

                def _run_dt():
                    engine = DigitalTwinDataGenerator()
                    return engine.generate(
                        assessment_result=job.result,
                        vehicle_type=job.result["vehicle_classification"]["type"],
                    )

                dt_success, dt_result = _run_stage_with_timeout(
                    _run_dt, "digital_twin", STAGE_TIMEOUTS["digital_twin"]
                )
                if dt_success and dt_result:
                    job.result["digital_twin"] = dt_result
                else:
                    logger.warning("Digital twin stage did not produce a result")
            except Exception:
                logger.exception("Digital twin generation failed (non-fatal)")

        if job.result and job.status == "completed":
            try:
                from infrastructure.neo4j_client import Neo4jClient
                from infrastructure.graph_repository import GraphRepository

                neo4j_client = Neo4jClient()
                if neo4j_client.connect():
                    graph_repo = GraphRepository(neo4j_client)
                    graph_repo.initialize_schema()
                    graph_repo.persist_assessment(
                        job.result, str(job_uuid), intake_id
                    )
                    similar = graph_repo.find_similar_retrofits(intake_id)
                    if similar:
                        job.result["similar_retrofits"] = similar
                else:
                    deg_mgr.register("neo4j", 1, "Neo4j connection failed — graph features unavailable")
            except Exception:
                logger.exception("Neo4j integration failed (non-fatal)")

        job.result = _make_json_safe(job.result)
        job.updated_at = datetime.now(tz.utc)
        db.commit()

        from core.sse import publish_job_event
        publish_job_event(intake_id, "job.completed", {
            "job_id": str(job_uuid),
            "status": job.status,
            "progress_pct": job.progress_pct,
        })

        logger.info("Job %s completed with status %s", job_uuid, job.status)

    except Exception:
        logger.exception("Assessment job %s failed unexpectedly", intake_id)
        db.rollback()
        try:
            job = (
                db.query(Job)
                .filter(Job.intake_id == uuid.UUID(intake_id))
                .order_by(Job.created_at.desc())
                .first()
            )
            if job:
                _fail_or_retry(job, db, intake_id)
        except Exception:
            logger.exception("Error during job failure handling")
    finally:
        db.close()


def _handle_timeout(
    job, db: DBSession, completed: list[str], total_stages: int, intake_id: str
) -> None:
    completed_set = set(completed)
    has_meaningful = MIN_STAGES_FOR_PARTIAL.issubset(completed_set)

    if has_meaningful:
        job.status = "partial_complete"
        job.result = {
            "assessment_state": "partial_assessment",
            "confidence_score": 55,
            "confidence_factors": {},
            "safety_overrides": ["Job timed out before full assessment"],
            "feasibility_score": 49,
            "feasibility_label": "conditionally_feasible",
            "vehicle_classification": {
                "type": "unknown",
                "confidence": 0.0,
                "human_confirmed": False,
                "alternatives": [],
            },
            "deviation_summary": {
                "anomalies_detected": 0,
                "severity": "unknown",
                "top_issues": ["Assessment incomplete due to timeout"],
            },
            "risk_summary": {
                "system_risk_state": "elevated",
                "critical_count": 0,
                "high_count": 1,
                "medium_count": 0,
                "low_count": 0,
            },
            "risks": [
                {
                    "category": "timeout",
                    "severity": "high",
                    "message": "Assessment timed out with partial results",
                    "recommendation": "Re-run assessment with higher quality images",
                    "blocking": True,
                    "confidence": 0.90,
                }
            ],
            "needs_confirmation": False,
            "compliance_state": "insufficient_evidence",
        }
        logger.info(
            "Job %s hard timeout - partial complete (%d stages done)",
            job.id,
            len(completed),
        )
    else:
        job.status = "timed_out"
        job.result = None
        logger.info(
            "Job %s hard timeout - no meaningful partial result (%d stages done)",
            job.id,
            len(completed),
        )

    job.current_stage = None
    job.progress_pct = min(int((len(completed) / total_stages) * 100), 100)
    job.updated_at = datetime.now(tz.utc)

    _maybe_auto_retry(job, db, intake_id)

    from core.sse import publish_job_event
    publish_job_event(intake_id, "job.completed", {
        "job_id": str(job.id),
        "status": job.status,
        "progress_pct": job.progress_pct,
    })

    db.commit()


def _maybe_auto_retry(job, db: DBSession, intake_id: str) -> None:
    if job.retry_count < job.max_retries:
        job.retry_count += 1
        job.status = "retrying"
        db.commit()

        from redis import Redis
        from rq import Queue

        from core.config import settings

        redis_conn = Redis.from_url(settings.redis_url)
        queue = Queue("retromind-jobs", connection=redis_conn)
        queue.enqueue(run_assessment, intake_id)
        logger.info(
            "Job %s re-enqueued (retry %d/%d)",
            job.id,
            job.retry_count,
            job.max_retries,
        )


def _fail_or_retry(job, db: DBSession, intake_id: str) -> None:
    job.status = "timed_out"
    job.updated_at = datetime.now(tz.utc)
    _maybe_auto_retry(job, db, intake_id)
    db.commit()
