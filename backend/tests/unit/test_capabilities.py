
import pytest

from core.capabilities import CapabilityRegistry
from core.config import settings


@pytest.fixture(autouse=True)
def _reset_registry():
    CapabilityRegistry.reset()
    yield
    CapabilityRegistry.reset()


class TestCapabilityRegistry:
    def test_default_all_disabled(self):
        assert CapabilityRegistry.has("pytorch") is False
        assert CapabilityRegistry.has("rllib") is False
        assert CapabilityRegistry.has("genai") is False
        assert CapabilityRegistry.has("freecad") is False
        assert CapabilityRegistry.all() == {}

    def test_probe_disabled_flag(self):
        ok = CapabilityRegistry.probe("pytorch", enabled=False, check_fn=lambda: True)
        assert ok is False
        assert CapabilityRegistry.has("pytorch") is False

    def test_probe_enabled_success(self):
        ok = CapabilityRegistry.probe("pytorch", enabled=True, check_fn=lambda: True)
        assert ok is True
        assert CapabilityRegistry.has("pytorch") is True

    def test_probe_enabled_failure(self):
        ok = CapabilityRegistry.probe("pytorch", enabled=True, check_fn=lambda: False)
        assert ok is False
        assert CapabilityRegistry.has("pytorch") is False

    def test_probe_check_fn_exception(self):
        def _explode():
            raise RuntimeError("check failed")

        ok = CapabilityRegistry.probe("pytorch", enabled=True, check_fn=_explode)
        assert ok is False

    def test_all_returns_copy(self):
        CapabilityRegistry.probe("a", True, lambda: True)
        CapabilityRegistry.probe("b", True, lambda: False)
        result = CapabilityRegistry.all()
        assert result == {"a": True, "b": False}
        result["a"] = False
        assert CapabilityRegistry.has("a") is True

    def test_reset_clears_everything(self):
        CapabilityRegistry.probe("pytorch", True, lambda: True)
        assert CapabilityRegistry.has("pytorch") is True
        CapabilityRegistry.reset()
        assert CapabilityRegistry.has("pytorch") is False
        assert CapabilityRegistry.all() == {}


class TestFeatureFlagsDefault:
    """Integration: feature flags in Settings default to expected values."""

    def test_enable_pytorch_default_false(self):
        assert settings.enable_pytorch is False

    def test_enable_rl_recommendations_default_false(self):
        assert settings.enable_rl_recommendations is False

    def test_enable_generative_design_default_false(self):
        assert settings.enable_generative_design is False

    def test_enable_cad_export_default_false(self):
        assert settings.enable_cad_export is False

    def test_optional_paths_default_empty(self):
        assert settings.rllib_checkpoint_path == ""
        assert settings.openai_api_key == ""
        assert settings.anthropic_api_key == ""

    def test_flag_override_via_env(self, monkeypatch):
        monkeypatch.setattr(settings, "enable_pytorch", True)
        assert settings.enable_pytorch is True

    def test_feature_flag_and_registry_integration(self):
        """End-to-end: enable flag + probe = available."""
        CapabilityRegistry.probe("pytorch", enabled=True, check_fn=lambda: True)
        assert CapabilityRegistry.has("pytorch") is True

        CapabilityRegistry.probe("pytorch", enabled=False, check_fn=lambda: True)
        assert CapabilityRegistry.has("pytorch") is False

    def test_all_flags_false_persists_after_probe(self):
        """Probing with disabled flag never makes a capability available."""
        CapabilityRegistry.probe("rllib", enabled=False, check_fn=lambda: True)
        assert CapabilityRegistry.has("rllib") is False

    def test_multiple_capabilities_independent(self):
        CapabilityRegistry.probe("pytorch", True, lambda: True)
        CapabilityRegistry.probe("freecad", True, lambda: False)
        CapabilityRegistry.probe("genai", False, lambda: True)
        assert CapabilityRegistry.has("pytorch") is True
        assert CapabilityRegistry.has("freecad") is False
        assert CapabilityRegistry.has("genai") is False
