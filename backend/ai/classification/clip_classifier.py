"""
CLIP-based zero-shot vehicle classifier for Indian three-wheelers and commercial vehicles.

Uses OpenAI CLIP (ViT-B/32) to classify vehicle images against make/model text prompts
defined from the OEM database. No fine-tuning required.

Key optimization: text embeddings are computed once and cached, only image embedding
is computed at inference time.
"""

import hashlib
import logging
import pickle
import re
import threading
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

PROMPT_TEMPLATES: dict[str, list[str]] = {
    "three_wheeler_passenger": [
        "a photo of a {make} {model} auto rickshaw",
        "a {make} {model} three wheeler passenger vehicle",
    ],
    "three_wheeler_cargo": [
        "a photo of a {make} {model} cargo three wheeler",
        "a {make} {model} goods auto rickshaw",
    ],
    "scooter": [
        "a photo of a {make} {model} scooter",
        "a {make} {model} motor scooter",
    ],
    "motorcycle": [
        "a photo of a {make} {model} motorcycle",
        "a {make} {model} bike",
    ],
    "hatchback": [
        "a photo of a {make} {model} hatchback car",
        "a {make} {model} car",
    ],
    "sedan": [
        "a photo of a {make} {model} sedan",
        "a {make} {model} car",
    ],
    "suv": [
        "a photo of a {make} {model} SUV",
        "a {make} {model} sport utility vehicle",
    ],
    "commercial": [
        "a photo of a {make} {model} commercial vehicle",
        "a {make} {model} truck",
    ],
    "ev": [
        "a photo of a {make} {model} electric vehicle",
        "a {make} {model} EV",
    ],
}

DEFAULT_TEMPLATES = ["a photo of a {make} {model} vehicle"]


_global_clip: "CLIPVehicleClassifier | None" = None


def get_clip_classifier(model_name: str = "openai/clip-vit-base-patch32") -> "CLIPVehicleClassifier":
    """Get or create the global CLIP classifier singleton."""
    global _global_clip
    if _global_clip is None:
        _global_clip = CLIPVehicleClassifier(model_name)
    return _global_clip


class CLIPVehicleClassifier:
    _load_lock = threading.Lock()

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        self.model_name = model_name
        self._model = None
        self._processor = None
        self._loaded = False
        self._text_cache_file = MODELS_DIR / "clip_text_embeddings.pkl"
        self._text_cache: dict[str, dict] = {}
        self._load_cache()

    def _load(self):
        if self._loaded:
            return True
        with self._load_lock:
            if self._loaded:
                return True
            try:
                import torch
                from transformers import CLIPModel, CLIPProcessor

                self._processor = CLIPProcessor.from_pretrained(self.model_name)
                self._model = CLIPModel.from_pretrained(self.model_name)
                self._model.eval()
                self._loaded = True
                logger.info("CLIP model %s loaded", self.model_name)
                return True
            except ImportError as e:
                logger.warning("CLIP dependencies not available: %s", e)
                return False
            except Exception as e:
                logger.warning("CLIP model load failed: %s (%s)", e, type(e).__name__)
                return False

    def _load_cache(self):
        if self._text_cache_file.exists():
            try:
                with open(self._text_cache_file, "rb") as f:
                    self._text_cache = pickle.load(f)
                logger.info("Loaded %d cached text embedding sets", len(self._text_cache))
            except Exception as e:
                logger.warning("Failed to load text embedding cache: %s", e)
                self._text_cache = {}

    def _save_cache(self):
        try:
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
            with open(self._text_cache_file, "wb") as f:
                pickle.dump(self._text_cache, f)
            logger.info("Saved %d cached text embedding sets", len(self._text_cache))
        except Exception as e:
            logger.warning("Failed to save text embedding cache: %s", e)

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def _cache_key(oem_models: list[dict], vehicle_type: str | None) -> str:
        raw = pickle.dumps(sorted([(m.get("id"), m.get("manufacturer_name"), m.get("model_name"), m.get("vehicle_type")) for m in oem_models]))
        raw += str(vehicle_type or "").encode()
        return hashlib.sha256(raw).hexdigest()

    def _build_prompts(
        self, oem_models: list[dict], vehicle_type: str | None = None
    ) -> list[dict]:
        prompts: list[dict] = []
        templates = PROMPT_TEMPLATES.get(vehicle_type or "", DEFAULT_TEMPLATES)
        for model in oem_models:
            make = model.get("manufacturer_name", model.get("make", ""))
            model_name = model.get("model_name", model.get("model", ""))
            if not make or not model_name:
                continue
            for template in templates:
                text = template.format(make=make, model=model_name)
                prompts.append({
                    "text": self._normalize_text(text),
                    "oem_model_id": model.get("id"),
                    "make": make,
                    "model": model_name,
                    "vehicle_type": model.get("vehicle_type", vehicle_type or ""),
                })
        if not prompts:
            logger.warning("No prompts built for vehicle_type=%s", vehicle_type)
        return prompts

    def _compute_text_embeddings(
        self, oem_models: list[dict], vehicle_type: str | None = None
    ) -> tuple:
        ckey = self._cache_key(oem_models, vehicle_type)
        if ckey in self._text_cache:
            cached = self._text_cache[ckey]
            return cached["embeddings"], cached["prompts"]

        self._load()
        import torch

        prompts = self._build_prompts(oem_models, vehicle_type)
        if not prompts:
            return None, []

        texts = [p["text"] for p in prompts]
        with torch.no_grad():
            text_inputs = self._processor(
                text=texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
            )
            text_embeds = self._model.get_text_features(**text_inputs).pooler_output
            text_embeds = text_embeds / text_embeds.norm(dim=-1, keepdim=True)

        self._text_cache[ckey] = {
            "embeddings": text_embeds.cpu(),
            "prompts": prompts,
            "oem_fingerprint": ckey,
        }
        self._save_cache()
        return text_embeds.cpu(), prompts

    def classify(
        self,
        image: np.ndarray,
        oem_models: list[dict],
        vehicle_type: str | None = None,
        top_k: int = 5,
        confidence_threshold: float = 0.0,
    ) -> dict:
        loaded = self._load()
        if not loaded:
            return {"top_prediction": None, "all_scores": [], "top_k": [], "threshold": confidence_threshold, "error": "model not loaded"}
        import torch

        text_embeds, prompts = self._compute_text_embeddings(oem_models, vehicle_type)
        if text_embeds is None:
            return {"top_prediction": None, "all_scores": [], "top_k": [], "threshold": confidence_threshold}

        with torch.no_grad():
            image_inputs = self._processor(
                images=[image],
                return_tensors="pt",
            )
            image_embeds = self._model.get_image_features(**image_inputs).pooler_output
            image_embeds = image_embeds / image_embeds.norm(dim=-1, keepdim=True)

            logits = (image_embeds @ text_embeds.T) * 100.0
            probs = logits.softmax(dim=-1).squeeze(0).cpu().numpy()

        scores = []
        for i, prompt in enumerate(prompts):
            scores.append({
                "oem_model_id": prompt["oem_model_id"],
                "make": prompt["make"],
                "model": prompt["model"],
                "vehicle_type": prompt["vehicle_type"],
                "score": float(probs[i]),
            })

        scores.sort(key=lambda x: x["score"], reverse=True)
        top_prediction = scores[0] if scores else None
        top_k_filtered = [s for s in scores[:top_k] if s["score"] >= confidence_threshold]

        return {
            "top_prediction": top_prediction,
            "all_scores": scores,
            "top_k": top_k_filtered,
            "threshold": confidence_threshold,
        }


class HeuristicCLIPFallback:
    def __init__(self, clip_classifier: CLIPVehicleClassifier | None = None):
        self.clip = clip_classifier or CLIPVehicleClassifier()

    def classify(
        self,
        image: np.ndarray,
        oem_models: list[dict],
        vehicle_type: str | None = None,
        clip_threshold: float = 0.3,
    ) -> dict:
        clip_result = self.clip.classify(
            image=image,
            oem_models=oem_models,
            vehicle_type=vehicle_type,
            top_k=5,
            confidence_threshold=clip_threshold,
        )
        if clip_result["top_prediction"] and clip_result["top_prediction"]["score"] >= clip_threshold:
            final = clip_result["top_prediction"]
        else:
            final = clip_result["top_k"][0] if clip_result["top_k"] else None
        return {"clip_result": clip_result, "final_prediction": final}
