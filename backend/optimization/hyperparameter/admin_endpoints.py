import logging
import threading

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_runner():
    from optimization.hyperparameter.study_runner import StudyRunner
    return StudyRunner()


@router.post("/admin/optimization/run")
def run_optimization(
    n_trials: int = 100,
    db: Session = Depends(get_db),
):
    """Run Optuna hyperparameter search (offline, may take minutes)."""
    try:
        import optuna  # noqa: F401
    except ImportError:
        raise HTTPException(
            status_code=400,
            detail="optuna not installed. Install with: pip install retromind[optuna]",
        )

    runner = _get_runner()

    def _run():
        try:
            results = runner.run_all(db_session=db)
            logger.info("Optimization complete: %s", results)
        except Exception:
            logger.exception("Optimization failed")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {
        "status": "started",
        "n_trials": n_trials,
        "targets": list(runner.TARGETS.keys()),
    }


@router.get("/admin/optimization/status")
def optimization_status():
    """Check latest optimization results."""
    from optimization.hyperparameter.study_runner import StudyRunner

    results = StudyRunner.load_best_params()
    if not results:
        return {"status": "never_run"}
    return {"status": "completed", "results": results}
