import logging
import os

import numpy as np

from core.capabilities import CapabilityRegistry
from core.config import settings
from core.retry import with_retry

logger = logging.getLogger(__name__)

MODEL_CLASSES = ["three_wheeler", "motorcycle", "four_wheeler", "unknown"]


class PyTorchRunner:
    """Same interface as ONNXRunner: load() -> bool, run(tensor) -> dict.

    Attempts to load a TorchScript model. Falls back gracefully if
    PyTorch is not installed or the model file is missing.
    """

    def __init__(self, model_path: str = None):
        self._model = None
        self._device = None
        self._model_path = model_path or settings.torch_model_path

    def load(self) -> bool:
        if not settings.enable_pytorch:
            logger.debug("PyTorch disabled via feature flag")
            return False
        if not self._model_path or not os.path.isfile(self._model_path):
            logger.debug("PyTorch model not found at %s", self._model_path)
            return False
        try:
            import torch
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._model = torch.jit.load(self._model_path, map_location=self._device)
            self._model.eval()
            CapabilityRegistry.probe("pytorch", True, lambda: True)
            logger.info(
                "PyTorch model loaded from %s (device: %s)",
                self._model_path, self._device,
            )
            return True
        except ImportError:
            CapabilityRegistry.probe("pytorch", False, lambda: False)
            logger.warning("PyTorch not installed — pip install retromind[torch]")
            return False
        except Exception:
            logger.exception("Failed to load PyTorch model from %s", self._model_path)
            CapabilityRegistry.probe("pytorch", False, lambda: False)
            return False

    @with_retry(retryable_exceptions=(RuntimeError,))
    def run(self, input_tensor: np.ndarray) -> dict | None:
        if self._model is None:
            return None
        try:
            import torch
            with torch.no_grad():
                tensor = torch.from_numpy(input_tensor).to(self._device)
                logits = self._model(tensor).cpu().numpy()
                probs = self._softmax(logits)
                return {
                    "logits": logits.tolist(),
                    "probabilities": probs.tolist(),
                    "predicted_class": int(np.argmax(logits, axis=1)[0]),
                }
        except RuntimeError:
            raise
        except Exception:
            logger.exception("PyTorch inference failed")
            return None

    def is_loaded(self) -> bool:
        return self._model is not None

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return e_x / np.sum(e_x, axis=-1, keepdims=True)
