from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from ai.classification.classifier import VehicleClassifier
from ai.models.pytorch_runner import PyTorchRunner, MODEL_CLASSES
from core.capabilities import CapabilityRegistry


@pytest.fixture(autouse=True)
def _reset_registry():
    CapabilityRegistry.reset()
    yield
    CapabilityRegistry.reset()


class TestPyTorchRunner:
    def test_init_defaults(self):
        runner = PyTorchRunner()
        assert runner._model is None
        assert not runner.is_loaded()

    def test_load_disabled_by_feature_flag(self):
        with patch("ai.models.pytorch_runner.settings") as mock_settings:
            mock_settings.enable_pytorch = False
            mock_settings.torch_model_path = "/fake/model.pt"
            runner = PyTorchRunner(model_path="/fake/model.pt")
            assert runner.load() is False

    def test_load_model_not_found(self):
        with patch("ai.models.pytorch_runner.settings") as mock_settings:
            mock_settings.enable_pytorch = True
            mock_settings.torch_model_path = "/nonexistent/model.pt"
            runner = PyTorchRunner()
            assert runner.load() is False

    def test_load_import_error(self):
        with patch("ai.models.pytorch_runner.settings") as mock_settings:
            mock_settings.enable_pytorch = True
            mock_settings.torch_model_path = "/fake/path"
            with patch("ai.models.pytorch_runner.os.path.isfile", return_value=True):
                with patch("ai.models.pytorch_runner.CapabilityRegistry.probe") as _:
                    runner = PyTorchRunner()
                    result = runner.load()
                    assert result is False

    def test_run_without_loaded_model(self):
        runner = PyTorchRunner()
        tensor = np.random.randn(1, 3, 224, 224).astype(np.float32)
        assert runner.run(tensor) is None

    def test_softmax(self):
        logits = np.array([[2.0, 1.0, 0.1, 0.0]])
        probs = PyTorchRunner._softmax(logits)
        assert abs(probs.sum() - 1.0) < 1e-6
        assert probs[0][0] > probs[0][1]

    def test_model_classes_defined(self):
        assert len(MODEL_CLASSES) == 4
        assert "three_wheeler" in MODEL_CLASSES
        assert "unknown" in MODEL_CLASSES


class TestVehicleClassifierPyTorch:
    def test_init_falls_back_to_onnx(self):
        with patch("ai.classification.classifier.ONNXRunner") as mock_onnx:
            mock_onnx_instance = MagicMock()
            mock_onnx_instance.load.return_value = True
            mock_onnx.return_value = mock_onnx_instance
            classifier = VehicleClassifier()
            assert classifier._onnx_loaded is True
            assert not classifier._pytorch_loaded

    def test_classify_pytorch_first(self):
        with patch("ai.classification.classifier.settings") as mock_settings:
            mock_settings.enable_pytorch = True
            with patch("ai.classification.classifier.ONNXRunner") as mock_onnx:
                mock_onnx_instance = MagicMock()
                mock_onnx_instance.load.return_value = True
                mock_onnx.return_value = mock_onnx_instance
                classifier = VehicleClassifier()
                classifier._pytorch_loaded = True
                classifier._pytorch_runner = MagicMock()
                classifier._pytorch_runner.run.return_value = {
                    "predicted_class": 0,
                    "probabilities": [[0.8, 0.1, 0.05, 0.05]],
                }

                with patch("os.path.isfile", return_value=True), patch(
                    "ai.classification.classifier.preprocess_for_classification",
                    return_value=np.ones((1, 3, 224, 224), dtype=np.float32),
                ):
                    result = classifier.classify({"left_side_profile": "/fake.jpg"})
                    assert result["vehicle_type"] == "three_wheeler"
                    assert result["model_loaded"] is True

    def test_classify_pytorch_fallback_to_onnx(self):
        with patch("ai.classification.classifier.ONNXRunner") as mock_onnx:
            mock_onnx_instance = MagicMock()
            mock_onnx_instance.load.return_value = True
            mock_onnx_instance.run.return_value = {
                "predicted_class": 1,
                "probabilities": [[0.1, 0.7, 0.1, 0.1]],
            }
            mock_onnx.return_value = mock_onnx_instance
            classifier = VehicleClassifier()
            classifier._pytorch_loaded = True
            classifier._pytorch_runner = MagicMock()
            classifier._pytorch_runner.run.return_value = None

            with patch("os.path.isfile", return_value=True), patch(
                "ai.classification.classifier.preprocess_for_classification",
                return_value=np.ones((1, 3, 224, 224), dtype=np.float32),
            ):
                result = classifier.classify({"left_side_profile": "/fake.jpg"})
                assert result["vehicle_type"] == "motorcycle"
                assert result["model_loaded"] is True

    def test_classify_onnx_fallback_to_heuristic(self):
        with patch("ai.classification.classifier.ONNXRunner") as mock_onnx:
            mock_onnx_instance = MagicMock()
            mock_onnx_instance.load.return_value = True
            mock_onnx_instance.run.return_value = None
            mock_onnx.return_value = mock_onnx_instance
            classifier = VehicleClassifier()

            with patch("os.path.isfile", return_value=True), patch(
                "ai.classification.classifier.preprocess_for_classification",
                return_value=np.ones((1, 3, 224, 224), dtype=np.float32),
            ):
                result = classifier.classify({"left_side_profile": "/fake.jpg"})
                assert "vehicle_type" in result
                assert result["human_confirmed"] is False


class TestTrainPyTorch:
    def test_import_error(self):
        with patch("ai.train_pytorch.train_pytorch") as mock:
            mock.return_value = {"success": False, "error": "PyTorch not installed"}
            result = mock()
            assert result["success"] is False
            assert "PyTorch" in result["error"]
