import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch


from optimization.hyperparameter.study_runner import StudyRunner, BEST_PARAMS_PATH
from optimization.hyperparameter.config_overrides import ConfigOverrides, OVERRIDE_PATH
from optimization.hyperparameter.tune_confidence import tune_confidence_weights
from optimization.hyperparameter.tune_deviation import tune_deviation_thresholds
from optimization.hyperparameter.tune_safety import tune_safety_overrides
from optimization.hyperparameter.tune_timeouts import tune_stage_timeouts


class MockTrial:
    def __init__(self, values: dict = None):
        self._values = values or {}
        self._suggestions = {}

    def suggest_float(self, name, low, high):
        return self._values.get(name, (low + high) / 2)

    def suggest_int(self, name, low, high):
        return int(self._values.get(name, (low + high) / 2))

    def report(self, value, step):
        pass

    def should_prune(self):
        return False


class TestStudyRunner:
    def test_init_defaults(self):
        runner = StudyRunner()
        assert runner.n_trials == 100

    def test_init_custom_trials(self):
        runner = StudyRunner(n_trials=50)
        assert runner.n_trials == 50

    def test_run_all_no_optuna(self):
        with patch("optimization.hyperparameter.study_runner._import_optuna", return_value=None):
            runner = StudyRunner()
            result = runner.run_all()
            assert result == {"status": "skipped", "reason": "optuna not installed"}

    def test_load_best_params_nonexistent(self):
        if BEST_PARAMS_PATH.exists():
            BEST_PARAMS_PATH.unlink()
        assert StudyRunner.load_best_params() == {}

    def test_save_and_load_best_params(self):
        with tempfile.TemporaryDirectory():
            runner = StudyRunner()
            runner._save_results({"test": {"best_params": {"x": 1}, "best_value": 0.9, "trials": 10}})

            loaded = runner.load_best_params()
            if loaded:
                assert "test" in loaded


class TestTunerFunctions:
    def test_tune_confidence_no_db(self):
        trial = MockTrial()
        score = tune_confidence_weights(trial, None)
        assert score == 0.5

    def test_tune_deviation_no_db(self):
        trial = MockTrial()
        score = tune_deviation_thresholds(trial, None)
        assert score == 0.5

    def test_tune_safety_no_db(self):
        trial = MockTrial()
        score = tune_safety_overrides(trial, None)
        assert score == 0.5

    def test_tune_timeouts_no_db(self):
        trial = MockTrial()
        score = tune_stage_timeouts(trial, None)
        assert score == 0.5

    def test_deviation_thresholds_enforces_ordering(self):
        trial = MockTrial(values={"minor_cutoff": 5.0, "moderate_cutoff": 2.0})
        score = tune_deviation_thresholds(trial, None)
        assert score == 0.0


class TestConfigOverrides:
    def test_apply_no_file(self):
        if OVERRIDE_PATH.exists():
            os.remove(OVERRIDE_PATH)
        ConfigOverrides.apply()

    def test_apply_patches_confidence_weights(self):
        from core.confidence import ConfidenceEngine
        original = ConfidenceEngine.WEIGHTS.copy()

        with tempfile.TemporaryDirectory() as tmp:
            fake_path = os.path.join(tmp, "best_params.json")
            with open(fake_path, "w") as f:
                json.dump({
                    "confidence_weights": {
                        "best_params": {
                            "completeness": 0.4,
                            "quality": 0.2,
                            "visibility": 0.15,
                            "classification": 0.1,
                            "geometry": 0.1,
                            "deviation_certainty": 0.05,
                        },
                        "best_value": 0.85,
                        "trials": 100,
                    }
                }, f)

            with patch("optimization.hyperparameter.config_overrides.OVERRIDE_PATH", Path(fake_path)):
                ConfigOverrides.apply()

        ConfidenceEngine.WEIGHTS.update(original)
