import logging
from typing import Optional

import numpy as np
from gymnasium import Env, spaces

logger = logging.getLogger(__name__)

_PRIORITY_MAP = {"low": 0, "medium": 1, "high": 2}

OBS_LOW = np.array([0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
OBS_HIGH = np.array([3.0, 100.0, 100.0, 3.0, 5.0], dtype=np.float32)

ACT_LOW = np.array([-1.0, 0.8, -1.0], dtype=np.float32)
ACT_HIGH = np.array([2.0, 1.5, 1.0], dtype=np.float32)


class RetroMindEnv(Env):
    """Gymnasium environment for training the RL recommendation agent.

    Wraps historical assessment data from FeedbackStore. Each step presents
    one assessment state vector; the agent chooses an action, which is compared
    to the historical action taken for that state. Reward reflects similarity
    to accepted actions (or dissimilarity from rejected ones).

    Observation space: 5-dim continuous (vehicle_type, confidence, avg_factor,
                        deviation_severity, degradation_tier)
    Action space:      3-dim continuous (priority_shift, cost_multiplier,
                        safety_escalation)
    """

    def __init__(self, env_config: Optional[dict] = None):
        super().__init__()
        env_config = env_config or {}

        self.observation_space = spaces.Box(low=OBS_LOW, high=OBS_HIGH, dtype=np.float32)
        self.action_space = spaces.Box(low=ACT_LOW, high=ACT_HIGH, dtype=np.float32)

        self._db = env_config.get("db_session")
        self._states: list[np.ndarray] = []
        self._actions: list[np.ndarray] = []
        self._rewards: list[float] = []
        self._idx = 0

        self._load_data()

    def _load_data(self):
        if self._db is None:
            logger.warning("No db_session — env will return zero states")
            return
        from infrastructure.feedback_store import FeedbackStore

        store = FeedbackStore(self._db)
        raw_states, raw_actions, raw_rewards = store.get_training_dataset(min_samples=1)

        for s, a, r in zip(raw_states, raw_actions, raw_rewards):
            if not s or not a:
                continue
            obs = np.asarray(s, dtype=np.float32)
            if obs.shape != (5,):
                logger.warning("Skipping state with unexpected shape %s", obs.shape)
                continue
            act = self._action_dict_to_array(a)
            self._states.append(obs)
            self._actions.append(act)
            self._rewards.append(float(r))

        logger.info("RetroMindEnv loaded %d transitions", len(self._states))

    @staticmethod
    def _action_dict_to_array(action_dict: dict) -> np.ndarray:
        priority = _PRIORITY_MAP.get(action_dict.get("priority_default", "medium"), 1)
        cost = float(action_dict.get("cost_multiplier", 1.0))
        cost = max(0.8, min(1.5, cost))
        safety = int(action_dict.get("safety_escalation", 0))
        return np.array([float(priority), cost, float(safety)], dtype=np.float32)

    def reset(self, *, seed: Optional[int] = None, options: Optional[dict] = None):
        super().reset(seed=seed)
        self._idx = 0
        if not self._states:
            return np.zeros(5, dtype=np.float32), {}
        return self._states[0].copy(), {}

    def step(self, action):
        if not self._states:
            return np.zeros(5, dtype=np.float32), 0.0, True, False, {}

        action = np.asarray(action, dtype=np.float32).flatten()
        if action.shape != (3,):
            action = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        historical_action = self._actions[self._idx]
        reward = self._compute_reward(action, historical_action, self._rewards[self._idx])

        self._idx += 1
        done = self._idx >= len(self._states)
        next_obs = self._states[0].copy() if done else self._states[self._idx].copy()
        return next_obs, reward, done, False, {}

    @staticmethod
    def _compute_reward(chosen: np.ndarray, historical: np.ndarray, was_accepted: float) -> float:
        normalizer = np.array([2.0, 0.7, 2.0], dtype=np.float32)
        norm_diff = np.abs(chosen - historical) / normalizer
        distance = float(np.mean(np.clip(norm_diff, 0.0, 1.0)))
        similarity = 1.0 - distance
        return float(similarity * was_accepted)
