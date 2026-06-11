import logging
import threading

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import get_admin_user
from core.capabilities import CapabilityRegistry
from core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/admin/rl/train")
def train_rl(
    num_iterations: int = 100,
    admin: str = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Train RL recommendation agent from historical feedback data."""
    try:
        import ray  # noqa: F401
        from ray.rllib.algorithms.ppo import PPOConfig  # noqa: F401
    except ImportError:
        raise HTTPException(
            status_code=400,
            detail="ray[rllib] not available. Install with: pip install retromind[rllib]",
        )
    CapabilityRegistry.probe("rllib", True, lambda: True)

    from ai.recommendations.train_rl import train_rl_from_history

    result = {}

    def _run():
        try:
            r = train_rl_from_history(db, num_iterations=num_iterations)
            result.update(r)
            logger.info("RL training complete: %s", r)
        except Exception:
            logger.exception("RL training failed")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {
        "status": "started",
        "num_iterations": num_iterations,
        "detail": "Training running in background. Check logs for results.",
    }


@router.get("/admin/rl/status")
def rl_training_status():
    """Check if RL agent is loaded and capability status."""
    rllib_available = False
    try:
        import ray  # noqa: F401
        from ray.rllib.algorithms.ppo import PPOConfig  # noqa: F401
        rllib_available = True
    except ImportError:
        pass
    return {
        "rllib_available": rllib_available,
        "rllib_probed": CapabilityRegistry.has("rllib_probed"),
    }
