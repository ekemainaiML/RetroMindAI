import json
import logging
from typing import ClassVar

from core.config import Settings, settings

logger = logging.getLogger(__name__)

REDIS_KEY = "retromind:feature_overrides"


class FeatureFlagStore:
    _overrides: ClassVar[dict[str, bool]] = {}

    FEATURE_FLAGS = {
        "enable_optuna": {
            "label": "Hyperparameter Optimization",
            "description": "Optuna-powered tuning of ML model hyperparameters",
            "dep": "pip install retromind[optuna]",
            "dep_installed": False,
        },
        "enable_pytorch": {
            "label": "PyTorch CNN Classifier",
            "description": "MobileNetV3-small CNN for vehicle type classification",
            "dep": "pip install retromind[torch]",
            "dep_installed": False,
        },
        "enable_rl_recommendations": {
            "label": "RLlib Adaptive Recommendations",
            "description": "PPO agent that learns recommendation adjustments from feedback",
            "dep": "pip install retromind[rllib]",
            "dep_installed": False,
        },
        "enable_generative_design": {
            "label": "Generative AI Refinement",
            "description": "OpenAI/Anthropic refinement of battery zones and wiring routes",
            "dep": "pip install retromind[genai]",
            "dep_installed": False,
        },
        "enable_cad_export": {
            "label": "FreeCAD CAD Export",
            "description": "STEP/STL 3D model export via FreeCAD worker container",
            "dep": "docker compose --profile freecad up",
            "dep_installed": False,
        },
    }

    # Snapshot of env-var-derived flag values before runtime overrides
    _env_values: ClassVar[dict[str, bool]] = {}

    @classmethod
    def init(cls):
        for name in cls.FEATURE_FLAGS:
            cls._env_values[name] = getattr(settings, name, False)
        cls.load_overrides()

    @classmethod
    def probe_dependencies(cls):
        for name, info in cls.FEATURE_FLAGS.items():
            dep = info["dep"]
            installed = False
            try:
                if "optuna" in dep:
                    try:
                        import importlib
                        importlib.import_module("optuna")
                        installed = True
                    except Exception:
                        installed = False
                elif "torch" in dep:
                    try:
                        import importlib
                        importlib.import_module("torch")
                        installed = True
                    except Exception:
                        installed = False
                elif "rllib" in dep:
                    try:
                        import importlib
                        importlib.import_module("ray")
                        installed = True
                    except Exception:
                        installed = False
                elif "genai" in dep or "openai" in dep:
                    try:
                        import importlib
                        importlib.import_module("openai")
                        installed = True
                    except Exception:
                        installed = False
                else:
                    installed = False
            except Exception:
                installed = False
            info["dep_installed"] = installed

    @classmethod
    def get_effective(cls, name: str) -> bool:
        return cls._overrides.get(name, cls._env_values.get(name, False))

    @classmethod
    def set_override(cls, name: str, value: bool) -> bool:
        if name not in cls.FEATURE_FLAGS:
            return False
        cls._overrides[name] = value
        Settings._feature_overrides[name] = value
        try:
            from redis import Redis
            conn = Redis.from_url(settings.redis_url, socket_connect_timeout=1)
            existing = {}
            raw = conn.get(REDIS_KEY)
            if raw:
                existing = json.loads(raw)  # type: ignore[arg-type]
            existing[name] = value
            conn.set(REDIS_KEY, json.dumps(existing))
            conn.close()
        except Exception:
            logger.warning("Failed to persist feature override to Redis")
        logger.info("Feature flag '%s' set to %s (admin override)", name, value)
        return True

    @classmethod
    def load_overrides(cls):
        try:
            from redis import Redis
            conn = Redis.from_url(settings.redis_url, socket_connect_timeout=1)
            raw = conn.get(REDIS_KEY)
            if raw:
                cls._overrides = json.loads(raw)
                for k, v in cls._overrides.items():
                    Settings._feature_overrides[k] = v
            conn.close()
        except Exception:
            cls._overrides = {}

    @classmethod
    def all_flags(cls) -> list[dict]:
        cls.probe_dependencies()
        result = []
        for name, info in cls.FEATURE_FLAGS.items():
            result.append({
                "name": name,
                "label": info["label"],
                "description": info["description"],
                "env_value": cls._env_values.get(name, False),
                "runtime_override": cls._overrides.get(name),
                "effective": cls.get_effective(name),
                "dep_installed": info["dep_installed"],
                "dep": info["dep"],
            })
        return result
