import logging

logger = logging.getLogger(__name__)

DEFAULT_CHECKPOINT_DIR = "/app/ai/models/rl_checkpoint"


def train_rl_from_history(db_session, num_iterations: int = 100) -> dict:
    """Train a PPO agent on historical assessment + confirmation data.

    Uses RetroMindEnv which replays past (state, action, reward) transitions
    from FeedbackStore. The policy learns to match accepted actions and avoid
    rejected ones via a similarity-based reward signal.

    Args:
        db_session: SQLAlchemy session for querying feedback data.
        num_iterations: RLlib training iterations.

    Returns:
        dict with training results (success, reward, checkpoint_path, samples).
    """
    try:
        from ray.rllib.algorithms.ppo import PPOConfig
    except ImportError:
        return {
            "success": False,
            "error": "ray[rllib] not installed. Install with: pip install retromind[rllib]",
        }

    from ai.recommendations.env import RetroMindEnv
    from core.config import settings
    from infrastructure.feedback_store import FeedbackStore

    store = FeedbackStore(db_session)
    raw_states, raw_actions, raw_rewards = store.get_training_dataset(min_samples=10)

    if len(raw_states) < 10:
        return {
            "success": False,
            "error": f"Not enough feedback data ({len(raw_states)} samples, need 10)",
        }

    config = (
        PPOConfig()
        .environment(
            env=RetroMindEnv,
            env_config={"db_session": db_session},
        )
        .training(
            lr=0.0003,
            train_batch_size=min(4000, 512),
            sgd_minibatch_size=128,
            num_sgd_iter=10,
            gamma=0.99,
            lambda_=0.95,
            clip_param=0.2,
        )
        .resources(num_gpus=0)
    )

    algo = config.build()

    best_reward = float("-inf")
    for i in range(num_iterations):
        result = algo.train()
        reward_raw = result.get("episode_reward_mean", 0.0)
        reward = float(reward_raw) if reward_raw is not None else 0.0
        if reward > best_reward:
            best_reward = reward
        if (i + 1) % 10 == 0:
            logger.info(
                "RL iteration %d/%d: reward_mean=%.4f (best=%.4f)",
                i + 1, num_iterations, reward, best_reward,
            )

    checkpoint_dir = settings.rllib_checkpoint_path or DEFAULT_CHECKPOINT_DIR
    checkpoint_path = algo.save(checkpoint_dir=str(checkpoint_dir))
    logger.info("RL checkpoint saved to %s (best_reward=%.4f)", checkpoint_path, best_reward)

    return {
        "success": True,
        "checkpoint_path": str(checkpoint_path),
        "iterations": num_iterations,
        "best_reward": best_reward,
    }
