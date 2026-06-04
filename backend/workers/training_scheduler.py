import logging
import os
import shutil
import time
from datetime import datetime, timezone


from core.config import settings
from core.database import SessionLocal
from core.models import Job

logger = logging.getLogger(__name__)

MIN_TRAINING_SAMPLES = 3
RETRAIN_INTERVAL_SECONDS = 1800
TEMP_TRAINING_DIR = "/tmp/retrain_data"


def _get_heuristic_baseline() -> float:
    return 0.75


def _collect_training_data(db_session, output_dir: str) -> int:
    from core.models import Intake

    import cv2

    jobs = (
        db_session.query(Job)
        .join(Intake, Job.intake_id == Intake.id)
        .filter(
            Job.status == "completed",
            Job.result.isnot(None),
            Job.trained_on.is_(None),
        )
        .all()
    )

    os.makedirs(output_dir, exist_ok=True)
    count = 0
    for job in jobs:
        result = job.result or {}
        vc = result.get("vehicle_classification", {}) or {}
        vtype = vc.get("type", "unknown")
        slot_key = vtype.replace(" ", "_")

        intake = job.intake
        if not intake or not intake.view_slots:
            continue
        for slot_name, file_path in intake.view_slots.items():
            if not file_path:
                continue
            img = None
            if os.path.isfile(file_path):
                img = cv2.imread(file_path)
            elif str(file_path).startswith("demo://"):
                from tests.synthetic_images import _VEHICLE_PROTOTYPES, _render_vehicle
                proto = _VEHICLE_PROTOTYPES.get(vtype if vtype != "unknown" else "three_wheeler")
                if proto:
                    img = _render_vehicle(proto)
            if img is not None:
                label_dir = os.path.join(output_dir, slot_key)
                os.makedirs(label_dir, exist_ok=True)
                dest = os.path.join(label_dir, f"{slot_key}_{count}.jpg")
                cv2.imwrite(dest, img)
                count += 1

    return count


def _mark_jobs_trained(db_session):
    db_session.query(Job).filter(
        Job.status == "completed",
        Job.result.isnot(None),
        Job.trained_on.is_(None),
    ).update({"trained_on": datetime.now(timezone.utc)})
    db_session.commit()


def _seed_synthetic_training_data(db_session):
    """Generate synthetic training images from prototypes so the pipeline
    always has baseline data even without real uploaded jobs."""
    import cv2
    import numpy as np
    from tests.synthetic_images import _VEHICLE_PROTOTYPES, _render_vehicle

    output_dir = TEMP_TRAINING_DIR
    os.makedirs(output_dir, exist_ok=True)
    written = 0
    for vtype, proto in _VEHICLE_PROTOTYPES.items():
        label_dir = os.path.join(output_dir, vtype)
        os.makedirs(label_dir, exist_ok=True)
        existing = len(os.listdir(label_dir))
        needed = max(0, MIN_TRAINING_SAMPLES - existing)
        for i in range(needed):
            img = _render_vehicle(proto)
            for _ in range(3):
                angle = np.random.uniform(-15, 15)
                h, w = img.shape[:2]
                rot = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
                aug = cv2.warpAffine(img, rot, (w, h), borderValue=200)
                noise = np.random.normal(0, 5, aug.shape).astype(np.int16)
                aug = np.clip(aug.astype(np.int16) + noise, 0, 255).astype(np.uint8)
                dest = os.path.join(label_dir, f"syn_{vtype}_{written}.jpg")
                cv2.imwrite(dest, aug)
                written += 1
    if written:
        logger.info("Seeded %d synthetic training images", written)


def scheduled_retrain():
    """Called periodically by training-scheduler container."""
    db = SessionLocal()
    try:
        from ai.train_pytorch import train_pytorch

        unprocessed = (
            db.query(Job)
            .filter(
                Job.status == "completed",
                Job.result.isnot(None),
                Job.trained_on.is_(None),
            )
            .count()
        )

        if unprocessed < MIN_TRAINING_SAMPLES:
            logger.info(
                "Not enough new samples for retraining (%d < %d)",
                unprocessed, MIN_TRAINING_SAMPLES,
            )
            _seed_synthetic_training_data(db)
            return

        samples = _collect_training_data(db, TEMP_TRAINING_DIR)
        logger.info("Collected %d training samples", samples)

        if samples < MIN_TRAINING_SAMPLES:
            return

        model_path = "/app/ai/models/vehicle_classifier_autotrain.pt"
        result = train_pytorch(
            TEMP_TRAINING_DIR,
            model_output_path=model_path,
            num_epochs=20,
        )

        if not result.get("success"):
            logger.warning("Auto-training failed: %s", result.get("error"))
            return

        accuracy = result.get("accuracy", 0.0)
        baseline = _get_heuristic_baseline()

        if accuracy < baseline:
            logger.warning(
                "Auto-trained model accuracy (%.4f) below baseline (%.4f), skipping deploy",
                accuracy, baseline,
            )
            return

        deploy_path = settings.torch_model_path or "/app/ai/models/vehicle_classifier.pt"
        shutil.copy2(model_path, deploy_path)
        _mark_jobs_trained(db)
        logger.info(
            "Deployed auto-trained model with accuracy %.4f (%d samples)",
            accuracy, samples,
        )

        if settings.enable_optuna:
            try:
                from optimization.hyperparameter.study_runner import StudyRunner
                runner = StudyRunner()
                runner.run_all(db_session=db)
                logger.info("Optuna hyperparameter optimization completed after training")
            except Exception:
                logger.warning("Optuna optimization failed after training")

        if settings.enable_rl_recommendations:
            try:
                from ai.recommendations.train_rl import train_rl_from_history as train_rl
                rl_result = train_rl(db, num_iterations=50)
                if rl_result.get("success"):
                    rl_path = rl_result["checkpoint_path"]
                    settings.rllib_checkpoint_path = str(rl_path)
                    logger.info("RL training completed, checkpoint at %s", rl_path)
                else:
                    logger.warning("RL training skipped: %s", rl_result.get("error"))
            except Exception:
                logger.warning("RL training failed after model deploy")

    except ImportError:
        logger.warning(
            "PyTorch not available for auto-training — pip install retromind[torch]"
        )
    except Exception:
        logger.exception("Auto-training failed")
    finally:
        db.close()


def run_loop():
    logger.info("Training scheduler started (interval=%ds)", RETRAIN_INTERVAL_SECONDS)
    while True:
        scheduled_retrain()
        time.sleep(RETRAIN_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_loop()
