import builtins
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from ai.recommendations.rl_agent import RLRecommendationAgent
from core.capabilities import CapabilityRegistry


@pytest.fixture(autouse=True)
def _reset_registry():
    CapabilityRegistry.reset()
    yield
    CapabilityRegistry.reset()


@pytest.fixture
def sample_assessment():
    return {
        "vehicle_classification": {"type": "three_wheeler", "confidence": 0.85},
        "confidence_factors": {"hog": 0.8, "color": 0.7, "contour": 0.9},
        "deviation_result": {
            "deviations": [
                {"parameter": "wheelbase_mm", "severity": "major"},
                {"parameter": "overall_length_mm", "severity": "minor"},
            ],
            "salvage_potential": 60,
        },
        "degradations": [{"tier": 2}, {"tier": 1}],
    }


class TestRLRecommendationAgentInit:
    def test_init_defaults(self):
        agent = RLRecommendationAgent()
        assert agent._algorithm is None
        assert agent._checkpoint_path == ""

    def test_init_with_path(self):
        agent = RLRecommendationAgent(checkpoint_path="/tmp/ckpt")
        assert agent._checkpoint_path == "/tmp/ckpt"


class TestRLRecommendationAgentLoad:
    def test_load_disabled_by_feature_flag(self):
        with patch("ai.recommendations.rl_agent.settings") as mock_settings:
            mock_settings.enable_rl_recommendations = False
            agent = RLRecommendationAgent(checkpoint_path="/tmp/ckpt")
            assert agent.load() is False

    def test_load_checkpoint_none(self):
        with patch("ai.recommendations.rl_agent.settings") as mock_settings:
            mock_settings.enable_rl_recommendations = True
            mock_settings.rllib_checkpoint_path = ""
            agent = RLRecommendationAgent(checkpoint_path="")
            assert agent.load() is False

    def test_load_import_error(self, monkeypatch):
        with patch("ai.recommendations.rl_agent.settings") as mock_settings:
            mock_settings.enable_rl_recommendations = True
            mock_settings.rllib_checkpoint_path = "/tmp/ckpt"

            _original_import = builtins.__import__

            def _raise_import(name, *args, **kwargs):
                if name == "ray":
                    raise ImportError("No module named ray")
                return _original_import(name, *args, **kwargs)

            monkeypatch.setattr(builtins, "__import__", _raise_import)
            agent = RLRecommendationAgent(checkpoint_path="/tmp/ckpt")
            result = agent.load()
            assert result is False

    def test_load_success(self):
        with patch("ai.recommendations.rl_agent.settings") as mock_settings:
            mock_settings.enable_rl_recommendations = True
            mock_settings.rllib_checkpoint_path = "/tmp/ckpt"

            mock_algo = MagicMock()
            mock_ppo_module = MagicMock()
            mock_ppo = MagicMock()
            mock_ppo.from_checkpoint.return_value = mock_algo
            mock_ppo_module.PPO = mock_ppo

            _original_import = builtins.__import__

            def _mock_import(name, *args, **kwargs):
                if name == "ray.rllib.algorithms.ppo":
                    return mock_ppo_module
                if name == "ray" or name.startswith("ray."):
                    return MagicMock()
                return _original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", _mock_import):
                agent = RLRecommendationAgent(checkpoint_path="/tmp/ckpt")
                result = agent.load()
                assert result is True
                assert agent._algorithm is not None


class TestRLRecommendationAgentGenerate:
    def test_generate_returns_none_when_not_loaded(self, sample_assessment):
        agent = RLRecommendationAgent()
        assert agent.generate(sample_assessment) is None

    def test_generate_returns_adjustments_when_loaded(self, sample_assessment):
        agent = RLRecommendationAgent()
        agent._algorithm = MagicMock()
        agent._algorithm.compute_single_action.return_value = np.array([0, 1.0, 0])
        result = agent.generate(sample_assessment)
        assert result is not None
        assert result["rl_adjusted"] is True
        assert result["generated_by"] == "rl_agent"

    def test_generate_logs_failure_on_exception(self, sample_assessment):
        agent = RLRecommendationAgent()
        agent._algorithm = MagicMock()
        agent._algorithm.compute_single_action.side_effect = ValueError("bad action")

        with patch("ai.recommendations.rl_agent.get_degradation_manager") as mock_gdm:
            result = agent.generate(sample_assessment)
            assert result is None
            mock_gdm.return_value.register.assert_called_with(
                "rl_engine", 1, "RL inference failed"
            )


class TestBuildState:
    def test_build_state_three_wheeler(self, sample_assessment):
        agent = RLRecommendationAgent()
        state = agent._build_state(sample_assessment)
        assert isinstance(state, np.ndarray)
        assert state.shape == (5,)
        assert state[0] == 0.0  # three_wheeler

    def test_build_state_unknown_type(self):
        agent = RLRecommendationAgent()
        result = {
            "vehicle_classification": {"type": "unknown", "confidence": 0.3},
            "confidence_factors": {},
            "deviation_result": {"deviations": []},
            "degradations": [],
        }
        state = agent._build_state(result)
        assert state[0] == 3.0
        assert state[1] == 0.3

    def test_build_state_max_deviation(self):
        agent = RLRecommendationAgent()
        result = {
            "vehicle_classification": {"type": "four_wheeler", "confidence": 0.5},
            "confidence_factors": {"hog": 0.5},
            "deviation_result": {
                "deviations": [
                    {"parameter": "wheelbase_mm", "severity": "major"},
                    {"parameter": "overall_width_mm", "severity": "major"},
                ]
            },
            "degradations": [{"tier": 3}],
        }
        state = agent._build_state(result)
        assert state[0] == 2.0
        assert state[3] == 3.0
        assert state[4] == 3.0

    def test_build_state_empty_sections(self):
        agent = RLRecommendationAgent()
        result = {}
        state = agent._build_state(result)
        assert state[0] == 3.0
        assert state[1] == 0.0


class TestActionToAdjustments:
    def test_default_action(self):
        agent = RLRecommendationAgent()
        action = np.array([1, 1.0, 0])
        adj = agent._action_to_adjustments(action, {})
        assert adj["priority_default"] == "medium"
        assert adj["cost_multiplier"] == 1.0
        assert adj["safety_escalation"] == 0

    def test_cost_multiplier_clamping_low(self):
        agent = RLRecommendationAgent()
        action = np.array([2, 0.5, 0])
        adj = agent._action_to_adjustments(action, {})
        assert adj["cost_multiplier"] == 0.8
        assert adj["priority_default"] == "high"

    def test_cost_multiplier_clamping_high(self):
        agent = RLRecommendationAgent()
        action = np.array([2, 2.0, 1])
        adj = agent._action_to_adjustments(action, {})
        assert adj["cost_multiplier"] == 1.5
        assert adj["priority_default"] == "high"
        assert adj["safety_escalation"] == 1

    def test_scalar_action(self):
        agent = RLRecommendationAgent()
        action = np.array(1)
        adj = agent._action_to_adjustments(action, {})
        assert "rl_adjusted" in adj


class TestRecordFeedback:
    def test_record_feedback_calls_store(self):
        mock_store = MagicMock()
        state = np.array([1.0, 2.0, 3.0])
        action = {"priority_default": "high"}
        RLRecommendationAgent.record_feedback(mock_store, "assess-1", True, state, action)
        mock_store.log_feedback.assert_called_once_with(
            assessment_id="assess-1",
            state_features=[1.0, 2.0, 3.0],
            action_taken=action,
            was_accepted=True,
        )

    def test_record_feedback_handles_exception(self):
        mock_store = MagicMock()
        mock_store.log_feedback.side_effect = ValueError("db error")
        state = np.array([1.0])
        action = {}
        RLRecommendationAgent.record_feedback(mock_store, "assess-1", True, state, action)


class TestFeedbackStore:
    def test_log_feedback(self):
        from core.models import RecommendationFeedback
        from infrastructure.feedback_store import FeedbackStore

        mock_db = MagicMock()
        store = FeedbackStore(mock_db)
        store.log_feedback(
            assessment_id="00000000-0000-0000-0000-000000000001",
            state_features=[1.0, 0.5],
            action_taken={"priority_default": "high"},
            was_accepted=True,
        )
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert isinstance(added, RecommendationFeedback)
        assert added.was_accepted is True

    def test_get_training_dataset_insufficient(self):
        from infrastructure.feedback_store import FeedbackStore

        mock_db = MagicMock()
        mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
        store = FeedbackStore(mock_db)
        states, actions, rewards = store.get_training_dataset(min_samples=100)
        assert len(states) == 0

    def test_get_training_dataset_sufficient(self):
        from infrastructure.feedback_store import FeedbackStore

        mock_records = []
        for i in range(5):
            rec = MagicMock()
            rec.state_features = [float(i), float(i * 2)]
            rec.action_taken = {"priority_default": "high"}
            rec.was_accepted = True
            mock_records.append(rec)

        mock_db = MagicMock()
        mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = (
            mock_records
        )
        store = FeedbackStore(mock_db)
        states, actions, rewards = store.get_training_dataset(min_samples=3)
        assert len(states) == 5
        assert len(rewards) == 5
        assert rewards[0] == 1.0

    def test_get_training_dataset_handles_empty_state(self):
        mock_records = [
            MagicMock(state_features=[], action_taken={}, was_accepted=True),
            MagicMock(state_features=[1.0], action_taken={}, was_accepted=False),
        ]
        mock_db = MagicMock()
        mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = (
            mock_records
        )
        from infrastructure.feedback_store import FeedbackStore
        store = FeedbackStore(mock_db)
        states, actions, rewards = store.get_training_dataset(min_samples=1)
        assert len(states) == 1


class TestTrainRL:
    def test_import_error(self):
        from ai.recommendations.train_rl import train_rl_from_history

        mock_db = MagicMock()
        _original_import = builtins.__import__

        def _raise_import(name, *args, **kwargs):
            if name == "ray":
                raise ImportError("No module named ray")
            return _original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", _raise_import):
            result = train_rl_from_history(mock_db, num_iterations=10)
        assert result["success"] is False
        assert "not installed" in result["error"]

    def test_insufficient_samples(self):
        from ai.recommendations.train_rl import train_rl_from_history

        mock_db = MagicMock()
        mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_ppo_config = MagicMock()
        mock_ppo_config_instance = MagicMock()
        mock_ppo_config.return_value = mock_ppo_config_instance

        _original_import = builtins.__import__

        def _mock_import(name, *args, **kwargs):
            if name == "ray.rllib.algorithms.ppo":
                mock_module = MagicMock()
                mock_module.PPOConfig = mock_ppo_config
                return mock_module
            if name == "ray" or name.startswith("ray."):
                return MagicMock()
            return _original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", _mock_import):
            result = train_rl_from_history(mock_db, num_iterations=10)
        assert result["success"] is False
        assert "Not enough" in result["error"]


class TestRecommendationEngineRL:
    def test_rl_agent_lazy_init(self):
        from ai.recommendations.engine import RecommendationEngine

        engine = RecommendationEngine()
        assert engine._rl_agent is None
        agent = engine._get_rl_agent()
        assert agent is not None
        assert agent._algorithm is None

    def test_generate_no_rl_adjustments_when_not_loaded(self, sample_assessment):
        from ai.recommendations.engine import RecommendationEngine

        engine = RecommendationEngine()
        result = engine.generate(sample_assessment, vehicle_type="three_wheeler")
        assert "recommendations" in result
        assert result["feasibility_score"] > 0
        for rec in result["recommendations"]:
            assert "structural_trigger" not in rec

    def test_generate_with_rl_adjustments(self, sample_assessment):
        from ai.recommendations.engine import RecommendationEngine

        engine = RecommendationEngine()
        mock_agent = MagicMock()
        mock_agent.generate.return_value = {
            "rl_adjusted": True,
            "priority_default": "high",
            "cost_multiplier": 1.25,
            "safety_escalation": 1,
            "generated_by": "rl_agent",
        }
        engine._rl_agent = mock_agent

        result = engine.generate(sample_assessment, vehicle_type="three_wheeler")
        for rec in result["recommendations"]:
            assert rec["priority"] == "high"

    def test_generate_rl_cost_multiplier_changes_costs(self, sample_assessment):
        from ai.recommendations.engine import RecommendationEngine

        engine = RecommendationEngine()
        mock_agent = MagicMock()
        mock_agent.generate.return_value = {
            "rl_adjusted": True,
            "priority_default": "medium",
            "cost_multiplier": 1.5,
            "safety_escalation": 0,
            "generated_by": "rl_agent",
        }
        engine._rl_agent = mock_agent

        result = engine.generate(sample_assessment, vehicle_type="three_wheeler")
        battery_rec = next(r for r in result["recommendations"] if r["id"] == "battery_pack_location")
        assert battery_rec["estimated_cost_inr"]["low"] > 50000
        assert battery_rec["estimated_cost_inr"]["low"] == int(round(50000 * 1.5))

    def test_generate_rl_fallback_on_none(self, sample_assessment):
        from ai.recommendations.engine import RecommendationEngine

        engine = RecommendationEngine()
        mock_agent = MagicMock()
        mock_agent.generate.return_value = None
        engine._rl_agent = mock_agent

        result = engine.generate(sample_assessment, vehicle_type="three_wheeler")
        assert "recommendations" in result
        battery_rec = next(r for r in result["recommendations"] if r["id"] == "battery_pack_location")
        assert battery_rec["estimated_cost_inr"]["low"] == 50000

    def test_admin_endpoint_import(self):
        from ai.recommendations.admin_endpoints import router
        assert router is not None
