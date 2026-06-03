import logging
import os

import numpy as np

from core.config import settings
from core.retry import with_retry

logger = logging.getLogger(__name__)


class ONNXRunner:
    def __init__(self, model_path: str = None):
        self._session = None
        self._input_name = None
        self._output_name = None
        self._model_path = (
            model_path
            or os.getenv("AI_MODEL_PATH")
            or settings.ai_model_path
        )

    def load(self) -> bool:
        if not os.path.isfile(self._model_path):
            logger.warning(
                "ONNX model not found at %s — falling back to heuristic classification",
                self._model_path,
            )
            return False
        try:
            import onnxruntime as ort

            self._session = ort.InferenceSession(
                self._model_path,
                providers=(
                    ["CoreMLExecutionProvider", "CPUExecutionProvider"]
                    if ort.get_device() == "CPU"
                    else ort.get_available_providers()
                ),
            )
            self._input_name = self._session.get_inputs()[0].name
            self._output_name = self._session.get_outputs()[0].name
            logger.info("ONNX model loaded from %s", self._model_path)
            return True
        except Exception:
            logger.exception("Failed to load ONNX model from %s", self._model_path)
            return False

    @with_retry(retryable_exceptions=(RuntimeError,))
    def run(self, input_tensor: np.ndarray) -> dict | None:
        if self._session is None:
            logger.error("ONNX session not loaded")
            return None
        try:
            outputs = self._session.run(
                [self._output_name],
                {self._input_name: input_tensor.astype(np.float32)},
            )
            logits = outputs[0]
            probs = self._softmax(logits)
            return {
                "logits": logits.tolist(),
                "probabilities": probs.tolist(),
                "predicted_class": int(np.argmax(logits)),
            }
        except RuntimeError:
            raise
        except Exception:
            logger.exception("ONNX inference failed")
            return None

    def is_loaded(self) -> bool:
        return self._session is not None

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return e_x / np.sum(e_x, axis=-1, keepdims=True)
