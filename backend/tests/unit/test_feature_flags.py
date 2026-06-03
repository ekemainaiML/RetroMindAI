import pytest

from core.config import Settings
from core.feature_flags import FeatureFlagStore


class TestFeatureFlagStore:
    def test_init_snapshots_env_values(self):
        FeatureFlagStore.init()
        for name in FeatureFlagStore.FEATURE_FLAGS:
            assert name in FeatureFlagStore._env_values
            assert isinstance(FeatureFlagStore._env_values[name], bool)

    def test_get_effective_defaults_to_env(self):
        FeatureFlagStore.init()
        val = FeatureFlagStore.get_effective("enable_pytorch")
        assert val == FeatureFlagStore._env_values["enable_pytorch"]

    def test_set_override_changes_effective(self):
        FeatureFlagStore.init()
        original = FeatureFlagStore.get_effective("enable_pytorch")
        FeatureFlagStore.set_override("enable_pytorch", not original)
        assert FeatureFlagStore.get_effective("enable_pytorch") != original
        FeatureFlagStore.set_override("enable_pytorch", original)

    def test_set_override_updates_settings(self):
        FeatureFlagStore.init()
        FeatureFlagStore.set_override("enable_cad_export", True)
        from core.config import settings
        assert settings.enable_cad_export is True
        FeatureFlagStore.set_override("enable_cad_export", False)

    def test_set_override_unknown_returns_false(self):
        result = FeatureFlagStore.set_override("enable_nonexistent", True)
        assert result is False

    def test_all_flags_returns_all(self):
        FeatureFlagStore.init()
        FeatureFlagStore._overrides.clear()
        Settings._feature_overrides.clear()
        flags = FeatureFlagStore.all_flags()
        assert len(flags) == 5
        names = {f["name"] for f in flags}
        assert names == {
            "enable_optuna",
            "enable_pytorch",
            "enable_rl_recommendations",
            "enable_generative_design",
            "enable_cad_export",
        }

    def test_all_flags_structure(self):
        FeatureFlagStore.init()
        flags = FeatureFlagStore.all_flags()
        for f in flags:
            assert "name" in f
            assert "label" in f
            assert "description" in f
            assert "env_value" in f
            assert "runtime_override" in f
            assert "effective" in f
            assert "dep_installed" in f
            assert "dep" in f
            assert isinstance(f["env_value"], bool)
            assert isinstance(f["effective"], bool)

    def test_all_flags_env_value_not_overridden(self):
        Settings._feature_overrides.clear()
        FeatureFlagStore._overrides.clear()
        FeatureFlagStore.init()
        FeatureFlagStore.set_override("enable_pytorch", True)
        flags = FeatureFlagStore.all_flags()
        pytorch = next(f for f in flags if f["name"] == "enable_pytorch")
        assert pytorch["effective"] is True
        assert pytorch["env_value"] is False
        assert pytorch["runtime_override"] is True
        FeatureFlagStore.set_override("enable_pytorch", False)

    def test_runtime_override_none_when_not_set(self):
        FeatureFlagStore.init()
        FeatureFlagStore._overrides.clear()
        Settings._feature_overrides.clear()
        flags = FeatureFlagStore.all_flags()
        cad = next(f for f in flags if f["name"] == "enable_cad_export")
        assert cad["runtime_override"] is None

    def test_probe_dependencies_does_not_crash(self):
        FeatureFlagStore.probe_dependencies()
        for _, info in FeatureFlagStore.FEATURE_FLAGS.items():
            assert "dep_installed" in info
            assert isinstance(info["dep_installed"], bool)

    def test_double_override_toggles_back(self):
        FeatureFlagStore.init()
        FeatureFlagStore.set_override("enable_generative_design", True)
        assert FeatureFlagStore.get_effective("enable_generative_design") is True
        FeatureFlagStore.set_override("enable_generative_design", False)
        assert FeatureFlagStore.get_effective("enable_generative_design") is False

    def test_settings_getattribute_uses_override(self):
        FeatureFlagStore.init()
        from core.config import settings
        original = settings.enable_pytorch
        Settings._feature_overrides["enable_pytorch"] = True
        assert settings.enable_pytorch is True
        Settings._feature_overrides["enable_pytorch"] = original
        assert settings.enable_pytorch == original

    def test_multiple_overrides_independent(self):
        FeatureFlagStore.init()
        original_a = FeatureFlagStore.get_effective("enable_pytorch")
        original_b = FeatureFlagStore.get_effective("enable_rl_recommendations")
        FeatureFlagStore.set_override("enable_pytorch", not original_a)
        assert FeatureFlagStore.get_effective("enable_rl_recommendations") == original_b
        FeatureFlagStore.set_override("enable_pytorch", original_a)
