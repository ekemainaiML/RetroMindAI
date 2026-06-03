import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class FeedbackStore:
    """Logs recommendation acceptance/rejection for RL training."""

    def __init__(self, db: Session):
        self.db = db

    def log_feedback(self, assessment_id: str, state_features: list,
                     action_taken: dict, was_accepted: bool):
        from core.models import RecommendationFeedback

        record = RecommendationFeedback(
            id=uuid.uuid4(),
            assessment_id=uuid.UUID(assessment_id) if isinstance(assessment_id, str) else assessment_id,
            state_features=state_features,
            action_taken=action_taken,
            was_accepted=was_accepted,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(record)
        self.db.commit()
        logger.info(
            "Feedback recorded for assessment %s: accepted=%s",
            assessment_id, was_accepted,
        )

    def get_training_dataset(self, min_samples: int = 100) -> tuple:
        from core.models import RecommendationFeedback

        records = (
            self.db.query(RecommendationFeedback)
            .order_by(RecommendationFeedback.created_at.desc())
            .limit(10000)
            .all()
        )

        if len(records) < min_samples:
            return [], [], []

        states = [r.state_features for r in records if r.state_features]
        actions = [r.action_taken for r in records if r.action_taken]
        rewards = [1.0 if r.was_accepted else -1.0 for r in records if r.state_features]

        return states, actions, rewards
